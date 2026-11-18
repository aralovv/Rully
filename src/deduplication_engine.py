import sys, os
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sqlite3
import unicodedata
import re
import csv
from typing import Dict, List, Tuple, Any, Optional

def normalize_text(text: str) -> str:
    if not text:
        return ""
    # Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)
    # Standardize apostrophes / Uzbek tutuq belgilari: ’, ‘, `, ʻ, ʼ -> '
    text = re.sub(r"[\u02bb\u02bc\u2018\u2019\u0060\u00b4\u02ca\u02cb]", "'", text)
    # Normalize dashes and hyphens
    text = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015]", "-", text)
    # Normalize quotes « » “ ” " -> "
    text = re.sub(r"[\u00ab\u00bb\u201c\u201d]", '"', text)
    # Collapse multiple whitespaces
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text

def option_set_similarity(opts1: List[str], opts2: List[str]) -> float:
    s1 = set(normalize_text(o) for o in opts1 if o)
    s2 = set(normalize_text(o) for o in opts2 if o)
    if not s1 or not s2:
        return 0.0
    return len(s1.intersection(s2)) / len(s1.union(s2))

class DeduplicationEngine:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def run_deduplication(self, report_path: str = "data/reports/duplicate_report.csv") -> Dict[str, Any]:
        """
        Conservative Multi-Factor Deduplication:
        - Evaluates image hashes, normalized question text, complete option sets, and correct answers.
        - Category A: Different non-null image hashes -> DISTINCT_VISUAL_SCENARIO (Never exact match or conflict).
        - Category B: Same non-null image hash -> Compare options and correct answers.
        - Category C: Both images missing -> Compare complete option sets and correct answers.
        - Category D: Asymmetric image -> Flag as ASYMMETRIC_IMAGE_REVIEW (Never assumed identical or conflicting).
        - Does NOT alter question records or delete questions.
        """
        cur = self.conn.cursor()

        # Load all questions
        cur.execute("""
            SELECT q.id, q.canonical_hash, q.question_text, q.language, q.image_id, q.verification_status, i.sha256, i.filename
            FROM questions q
            LEFT JOIN images i ON q.image_id = i.id;
        """)
        questions = cur.fetchall()

        # Load all answers grouped by question
        cur.execute("SELECT question_id, option_key, answer_text, is_correct FROM answers ORDER BY question_id, sort_order;")
        answers_by_qid: Dict[str, List[Dict[str, Any]]] = {}
        for row in cur.fetchall():
            qid = row[0]
            answers_by_qid.setdefault(qid, []).append({
                "key": row[1],
                "text": row[2],
                "is_correct": bool(row[3])
            })

        reclassified_pairs = []

        # Group by language
        by_lang: Dict[str, List[Any]] = {}
        for q in questions:
            by_lang.setdefault(q[3], []).append(q)

        for lang, lang_questions in by_lang.items():
            normalized_map: Dict[str, List[Any]] = {}
            for q in lang_questions:
                norm = normalize_text(q[2])
                normalized_map.setdefault(norm, []).append(q)

            for norm_text, q_group in normalized_map.items():
                if len(q_group) > 1:
                    base_q = q_group[0]
                    base_opts = answers_by_qid.get(base_q[0], [])
                    base_opt_texts = [o["text"] for o in base_opts]
                    base_correct_list = [normalize_text(o["text"]) for o in base_opts if o["is_correct"]]
                    base_correct = base_correct_list[0] if base_correct_list else ""
                    base_img_sha = base_q[6]
                    base_img_fn = base_q[7]

                    for other_q in q_group[1:]:
                        other_opts = answers_by_qid.get(other_q[0], [])
                        other_opt_texts = [o["text"] for o in other_opts]
                        other_correct_list = [normalize_text(o["text"]) for o in other_opts if o["is_correct"]]
                        other_correct = other_correct_list[0] if other_correct_list else ""
                        other_img_sha = other_q[6]
                        other_img_fn = other_q[7]

                        opts_sim = option_set_similarity(base_opt_texts, other_opt_texts)

                        # Category A: Both have images, but different non-null image hashes
                        if base_img_sha is not None and other_img_sha is not None and base_img_sha != other_img_sha:
                            comp_type = "DISTINCT_VISUAL_SCENARIO"
                            status = "PRESERVED_DISTINCT"
                            details = f"Different visual assets (Img1: {base_img_fn} vs Img2: {other_img_fn}); prompt text shared by exam template"

                        # Category B: Both have images, and identical image hash
                        elif base_img_sha is not None and other_img_sha is not None and base_img_sha == other_img_sha:
                            if opts_sim >= 0.9 and base_correct == other_correct:
                                comp_type = "EXACT_TEXT_AND_ANSWER"
                                status = "CONFIRMED_MATCH"
                                details = f"Identical visual asset ({base_img_fn}), matching option set, and identical correct answer"
                            elif base_correct != other_correct:
                                comp_type = "CONFLICTING_CORRECT_ANSWER"
                                status = "CONFLICT_DETECTED"
                                details = f"Same visual asset ({base_img_fn}), but conflicting correct answers: '{base_correct}' vs '{other_correct}'"
                            else:
                                comp_type = "VARIANT_OPTIONS_SAME_IMAGE"
                                status = "POTENTIAL_DUPLICATE_REVIEW"
                                details = f"Same visual asset ({base_img_fn}), but variant option sets (similarity: {opts_sim:.2f})"

                        # Category C: Both images are missing (Text-only questions)
                        elif base_img_sha is None and other_img_sha is None:
                            if opts_sim >= 0.9 and base_correct == other_correct:
                                comp_type = "EXACT_TEXT_AND_ANSWER"
                                status = "CONFIRMED_MATCH"
                                details = f"Text-only question with matching option sets and identical correct answer"
                            elif opts_sim >= 0.9 and base_correct != other_correct:
                                comp_type = "CONFLICTING_CORRECT_ANSWER"
                                status = "CONFLICT_DETECTED"
                                details = f"Text-only question with matching option set but contradictory answers: '{base_correct}' vs '{other_correct}'"
                            else:
                                comp_type = "DISTINCT_OPTION_SUBCLAUSES"
                                status = "POTENTIAL_DUPLICATE_REVIEW"
                                details = f"Same prompt, but distinct option sets testing different subclauses (similarity: {opts_sim:.2f})"

                        # Category D: Asymmetric visual asset (one has image, other does not)
                        else:
                            comp_type = "ASYMMETRIC_IMAGE_REVIEW"
                            status = "POTENTIAL_DUPLICATE_REVIEW"
                            img_present = base_img_fn if base_img_sha else other_img_fn
                            details = f"Asymmetric image: One question has image ({img_present}), other is text-only"

                        reclassified_pairs.append({
                            "question_id_1": base_q[0],
                            "question_id_2": other_q[0],
                            "language": lang,
                            "comparison_type": comp_type,
                            "status": status,
                            "details": details
                        })

        # Write separate output CSV
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["question_id_1", "question_id_2", "language", "comparison_type", "status", "details"])
            for r in reclassified_pairs:
                writer.writerow([r["question_id_1"], r["question_id_2"], r["language"], r["comparison_type"], r["status"], r["details"]])

        # Summary statistics
        from collections import Counter
        type_counts = Counter(r["comparison_type"] for r in reclassified_pairs)
        status_counts = Counter(r["status"] for r in reclassified_pairs)

        return {
            "total_pairs_evaluated": len(reclassified_pairs),
            "by_type": dict(type_counts),
            "by_status": dict(status_counts),
            "report_path": report_path
        }

if __name__ == "__main__":
    db_file = "working_master_database.sqlite" if os.path.exists("working_master_database.sqlite") else "master_database.sqlite"
    conn = sqlite3.connect(db_file)
    dedup = DeduplicationEngine(conn)
    res = dedup.run_deduplication("data/reports/duplicate_report.csv")
    print("Conservative Deduplication Completed:")
    print(res)
    conn.close()
