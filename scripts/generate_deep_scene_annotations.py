import os
import json
import base64
import time
import sqlite3
import logging
import asyncio
import argparse
from typing import Dict, Any, List, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scene_annotator")

OUTPUT_FILE = os.path.join("data", "image_scenes.json")
DB_PATH = "master_database.sqlite"
IMAGE_DIR = os.path.join("data", "images", "original")

PROMPT_TEMPLATE = """Siz O‘zbekiston Yo‘l Harakati Qoidalari (YHQ) bo‘yicha oliy toifali ekspert-annotatorsiz.
Quyida rasmiy davlat imtihon savoli, uning to‘liq variantlari, rasmiy to‘g‘ri javobi, YHQ qoidasi moddasi va rasmi berilgan.

SAVOL: {question_text}
TOIFA: {category_name}
VARIANTLAR:
{options_text}
TO‘G‘RI JAVOB: {correct_key}) {correct_text}
RASMIY QOIDA MODDASI: {legal_ref}
RASMIY IZOH: {explanation}

VAZIFA:
Ushbu rasm va rasmiy faktlarga qat'iy tayangan holda, rasmning CHUQUR, TO‘LIQ VA MOSLASHUVCHAN VIZUAL PASPORTINI faqat va faqat quyidagi JSON formatida yozing.
E'tibor bering: Har bir rasmda har xil holat bo'lishi mumkin (ba'zida tartibga soluvchi, ba'zida svetofor, ba'zida faqat belgilar, ba'zida harakat traektoriyalari A/B/C, ba'zida tibbiy yordam yoki avtomobil texnik tuzilishi). Agar rasmdagi element mavjud bo'lmasa, uni "Mavjud emas" deb yozing, bor elementlarni esa mayda detallarigacha mukammal ochib bering:

{{
  "sahna_turi": "Aniq holat turi (masalan: Tartibga soluvchili chorraha / Svetoforli chorraha / Imtiyoz belgili chorraha / Teng ahamiyatli chorraha / Yo‘l belgilari va chiziqlari / Manyovr va quvib o‘tish (A, B, C traektoriyalar) / To‘xtash va to‘xtab turish / Temir yo‘l kesishmasi / Piyodalar o‘tish joyi / Avtotransport nosozligi / Birinchi tibbiy yordam)",
  "vizual_muhit_va_yo‘l": "Yo‘lning tuzilishi (bo‘laklar soni, qatnov qismi qoplamasi, ajratuvchi bo‘lak, yo‘l chiziqlari 1.1, 1.3, 1.5, 1.11 va b., ob-havo/kunduz-kecha yoki xona sharoiti)",
  "belgilar_va_chiziqlar": "Rasmdagi barcha yo‘l belgilari: har birining raqami va nomi (masalan: 2.1 'Asosiy yo‘l', 7.13 'Asosiy yo‘l yo‘nalishi', 3.20 'Quvib o‘tish taqiqlanadi'), ularning o‘rnatilgan joyi va qamrovi. Agar belgi bo‘lmasa: 'Yo‘l belgilari yo‘q'",
  "tartibga_soluvchi_yoki_svetofor": "Agar tartibga soluvchi (GAI) bo‘lsa: uning gavdasi qayerga qaragan, har ikkala qo‘llari holati (yonga yoyilganmi, o‘ng qo‘li oldingami, jezl ko‘tarilganmi) va kimlarga qaysi tomonga ruxsat/taqiq beradi. Agar svetofor bo‘lsa: asosiy va qo‘shimcha seksiyaning qaysi chirog‘i yonmoqda. Agar tartibga solinmagan bo‘lsa: 'Mavjud emas (tartibga solinmagan vaziyat)'",
  "ishtirokchilar_va_obyektlar": [
    {{
      "obyekt": "Rangi va turi (masalan: Ko‘k yengil avtomobil, Qizil Damas, Yashil yuk mashinasi, Oq avtobus, Tramvay, Velosiped, Piyoda, Qon to‘xtatuvchi bog‘lam)",
      "joylashuvi": "Aynan qaysi yo‘l, qator yoki nuqtada (masalan: Asosiy yo‘l o‘ng bo‘lagida, Ikkinchi darajali yo‘lda, Chorraha markazida, Qatnov qismi chetida)",
      "harakat_yonalishi_yoki_traektoriya": "Qayerga harakatlanmoqda (masalan: To‘g‘riga, Chapga burilish uchun burilish chirog‘i (povorotnik) yoqilgan, A traektoriya bo‘ylab, To‘xtab turibdi)",
      "holati_va_huquqi": "Harakatlanishiga ruxsat beriladimi yoki taqiqlanadimi va aniq sababi (kimga yo‘l berishi shart yoki kimdan ustunlikka ega)"
    }}
  ],
  "traektoriyalar_tahlili": "Agar rasmda A, B, C, D kabi harakat chiziqlari yoki variant harflari tasvirlangan bo‘lsa, har birining to‘g‘ri yoki noto‘g‘riligi va sababi. Agar harfli chiziqlar bo‘lmasa: 'Mavjud emas'",
  "otish_tartibi_yoki_yechim": "Chorrahada transport vositalarining 1-chi, 2-chi, 3-chi bo‘lib o‘tishining qat'iy navbati YOKI savolning to‘g‘ri javobiga olib keluvchi vizual-mantiqiy yechim",
  "yhq_qoidasi_va_asos": "O‘zbekiston YHQning tegishli aniq moddasi, bandi va to‘liq huquqiy asosi"
}}
"""

def load_existing_annotations() -> Dict[str, Any]:
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error reading existing {OUTPUT_FILE}: {e}")
    return {}

def save_annotations(data: Dict[str, Any]):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    temp_file = OUTPUT_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_file, OUTPUT_FILE)

def get_unique_image_questions(db_path: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
    SELECT cq.canonical_id, i.filename, cq.category_name, ct.question_text, cq.correct_option_key, cq.legal_reference, ct.explanation
    FROM canonical_questions cq
    JOIN images i ON cq.primary_image_id = i.id
    LEFT JOIN canonical_translations ct ON cq.canonical_id = ct.canonical_id AND ct.language = 'uz_latn'
    WHERE cq.has_image = 1
    GROUP BY i.filename
    ORDER BY 
      CASE WHEN cq.category_name LIKE '%Tartibga soluvchi%' OR ct.question_text LIKE '%tartibga soluvchi%' THEN 0
           WHEN cq.category_name LIKE '%Chorrah%' THEN 1
           ELSE 2 END,
      cq.canonical_id
    """)
    rows = c.fetchall()
    
    result = []
    for r in rows:
        canon_id = r[0]
        filename = r[1]
        category = r[2] or "Yo‘l harakati qoidalari"
        q_text = r[3] or ""
        corr_key = r[4] or "A"
        legal_ref = r[5] or ""
        explanation = r[6] or ""

        # Fetch options
        c.execute("""
        SELECT option_key, is_correct, text_uz_latn
        FROM canonical_answers
        WHERE canonical_id = ?
        ORDER BY sort_order
        """, (canon_id,))
        ans_rows = c.fetchall()
        options = []
        corr_text = ""
        for a in ans_rows:
            opt_k, is_corr, opt_txt = a[0], bool(a[1]), a[2] or ""
            options.append((opt_k, opt_txt, is_corr))
            if opt_k == corr_key or is_corr:
                corr_text = opt_txt

        result.append({
            "canonical_id": canon_id,
            "filename": filename,
            "category_name": category,
            "question_text": q_text,
            "options": options,
            "correct_key": corr_key,
            "correct_text": corr_text,
            "legal_ref": legal_ref,
            "explanation": explanation,
            "local_path": os.path.join(IMAGE_DIR, filename)
        })
    conn.close()
    return result

async def annotate_single_image(
    client: httpx.AsyncClient,
    api_key: str,
    q: Dict[str, Any],
    models: List[str] = ["gemini-flash-lite-latest", "gemini-flash-latest"]
) -> Optional[Dict[str, Any]]:
    # 1. Read image base64
    img_path = q["local_path"]
    if not os.path.exists(img_path):
        logger.warning(f"Image file not found: {img_path}")
        return None

    try:
        with open(img_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to read image {img_path}: {e}")
        return None

    options_text = "\n".join([f"{k}) {txt}" + (" (TO‘G‘RI JAVOB)" if is_corr else "") for k, txt, is_corr in q["options"]])
    prompt = PROMPT_TEMPLATE.format(
        question_text=q["question_text"],
        category_name=q["category_name"],
        options_text=options_text,
        correct_key=q["correct_key"],
        correct_text=q["correct_text"],
        legal_ref=q["legal_ref"],
        explanation=q["explanation"]
    )

    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/webp", "data": b64_data}}
            ]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        for attempt in range(3):
            try:
                resp = await client.post(url, json=payload, timeout=45.0)
                if resp.status_code == 200:
                    raw_json = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(raw_json)
                    parsed["canonical_id"] = q["canonical_id"]
                    parsed["filename"] = q["filename"]
                    parsed["category_name"] = q["category_name"]
                    return parsed
                elif resp.status_code in (429, 503):
                    sleep_sec = 3.0 * (attempt + 1)
                    logger.warning(f"Spike ({resp.status_code}) on {model} for {q['filename']}, sleeping {sleep_sec}s (attempt {attempt+1})...")
                    await asyncio.sleep(sleep_sec)
                    continue
                else:
                    logger.error(f"Error {resp.status_code} on {model} for {q['filename']}: {resp.text[:200]}")
                    break
            except Exception as e:
                logger.warning(f"Exception on {model} for {q['filename']}: {e}")
                await asyncio.sleep(2.0)
                await asyncio.sleep(1.0)
                break
    return None

async def main():
    parser = argparse.ArgumentParser(description="Generate deep visual scene annotations for all traffic images")
    parser.add_argument("--limit", type=int, default=1000, help="Number of images to annotate in this batch")
    parser.add_argument("--delay", type=float, default=0.25, help="Seconds to sleep between requests")
    parser.add_argument("--category", type=str, default=None, help="Filter by category substring")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not configured in .env!")
        return

    existing = load_existing_annotations()
    logger.info(f"Loaded {len(existing)} existing scene annotations from {OUTPUT_FILE}")

    questions = get_unique_image_questions(DB_PATH)
    logger.info(f"Total unique image questions in database: {len(questions)}")

    if args.category:
        questions = [q for q in questions if args.category.lower() in q["category_name"].lower()]
        logger.info(f"Filtered to {len(questions)} questions for category '{args.category}'")

    # Filter out already annotated
    pending = [q for q in questions if q["filename"] not in existing]
    logger.info(f"Pending to annotate: {len(pending)}")

    to_process = pending[:args.limit]
    total_to_process = len(to_process)
    logger.info(f"Starting batch of {total_to_process} images...")

    start_time = time.time()
    async with httpx.AsyncClient(timeout=50.0) as client:
        count = 0
        for idx, q in enumerate(to_process):
            annot = await annotate_single_image(client, api_key, q)
            if annot:
                existing[q["filename"]] = annot
                save_annotations(existing)
                count += 1
            else:
                logger.warning(f"  -> FAILED for {q['filename']}")
            
            # Progress update every 5 images or on last
            if (idx + 1) % 5 == 0 or (idx + 1) == total_to_process:
                elapsed = time.time() - start_time
                avg_speed = elapsed / (idx + 1)
                remaining_sec = avg_speed * (total_to_process - (idx + 1))
                percent = ((idx + 1) / total_to_process) * 100
                logger.info(f"[{idx+1}/{total_to_process}] ({percent:.1f}%) | Total saved: {len(existing)} | Avg: {avg_speed:.2f}s/img | Est. remaining: {remaining_sec/60:.1f}m")
            
            if args.delay > 0:
                await asyncio.sleep(args.delay)

    logger.info(f"Batch completed! Successfully processed {count}/{total_to_process} images. Total annotations in {OUTPUT_FILE}: {len(existing)}")

if __name__ == "__main__":
    asyncio.run(main())
