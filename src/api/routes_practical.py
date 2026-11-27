"""
Practical Driving Exam (Amaliy Imtihon) API endpoints for RULLY Mini App.
Provides core instructional modules and step-by-step practice guidance.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.deps import get_current_user, get_db
from src.bot.database import BotDatabase
from src.amaliy_curriculum import PRACTICAL_MODULES

router = APIRouter(prefix="/api/amaliy", tags=["Practical Exam"])

PRACTICAL_BADGE_LOCALIZATION = {
    "Baza": {"uz_latn": "Baza", "uz_cyrl": "База", "ru": "Базовый"},
    "Asosiy": {"uz_latn": "Asosiy", "uz_cyrl": "Асосий", "ru": "Основной"},
    "Avtodrom": {"uz_latn": "Avtodrom", "uz_cyrl": "Автодром", "ru": "Автодром"},
    "Shahar": {"uz_latn": "Shahar", "uz_cyrl": "Шаҳар", "ru": "Город"},
    "Xavfsizlik": {"uz_latn": "Xavfsizlik", "uz_cyrl": "Хавфсизлик", "ru": "Безопасность"},
    "Yakunlash": {"uz_latn": "Yakunlash", "uz_cyrl": "Якунлаш", "ru": "Финал"}
}

def localize_badge(badge_raw: Any, lang: str) -> str:
    if isinstance(badge_raw, dict):
        return badge_raw.get(lang, badge_raw.get("uz_latn", "Baza"))
    return PRACTICAL_BADGE_LOCALIZATION.get(badge_raw, {}).get(lang, str(badge_raw) if badge_raw else "Baza")

def get_valid_lang(lang: Optional[str], default_lang: str = "uz_latn") -> str:
    if lang in ["uz_latn", "uz_cyrl", "ru"]:
        return lang
    if default_lang in ["uz_latn", "uz_cyrl", "ru"]:
        return default_lang
    return "uz_latn"

# 1. Modules List
@router.get("/modules")
def list_modules(
    lang: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    selected_lang = get_valid_lang(lang, user.get("language", "uz_latn"))
    completed_set = set(db.get_completed_modules(user["user_id"]))
    result = []
    for m in PRACTICAL_MODULES:
        is_done = m["id"] in completed_set
        result.append({
            "id": m["id"],
            "order": m["order"],
            "title": m["title"].get(selected_lang, m["title"]["uz_latn"]),
            "description": m["description"].get(selected_lang, m["description"]["uz_latn"]),
            "badge": localize_badge(m.get("badge", "Baza"), selected_lang),
            "duration_min": m.get("duration_min", 15),
            "steps_count": len(m.get("steps", [])),
            "is_completed": is_done
        })

    completed_count = sum(1 for item in result if item["is_completed"])
    total_count = len(result)
    pct = round((completed_count / total_count * 100), 1) if total_count > 0 else 0.0

    return {
        "language": selected_lang,
        "total": total_count,
        "completed_count": completed_count,
        "completion_percentage": pct,
        "modules": result
    }

class ModuleToggleRequest(BaseModel):
    module_id: str

@router.post("/modules/toggle")
def toggle_module(
    req: ModuleToggleRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    new_state = db.toggle_completed_module(user["user_id"], req.module_id)
    return {"ok": True, "module_id": req.module_id, "is_completed": new_state}

# 2. Module Detail
@router.get("/modules/{module_id}")
def get_module_detail(
    module_id: str,
    lang: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    selected_lang = get_valid_lang(lang, user.get("language", "uz_latn"))
    mod = next((m for m in PRACTICAL_MODULES if m["id"] == module_id), None)
    if not mod:
        raise HTTPException(status_code=404, detail="Module not found")

    steps = [
        {
            "step": s["step"],
            "title": s["title"].get(selected_lang, s["title"]["uz_latn"]),
            "instruction": s["instruction"].get(selected_lang, s["instruction"]["uz_latn"])
        }
        for s in mod.get("steps", [])
    ]

    mistakes = mod.get("common_mistakes", {}).get(selected_lang, mod.get("common_mistakes", {}).get("uz_latn", []))
    trap = mod.get("disqualification_trap", {}).get(selected_lang, mod.get("disqualification_trap", {}).get("uz_latn", ""))
    is_done = db.is_module_completed(user["user_id"], module_id)

    return {
        "id": mod["id"],
        "order": mod["order"],
        "title": mod["title"].get(selected_lang, mod["title"]["uz_latn"]),
        "description": mod["description"].get(selected_lang, mod["description"]["uz_latn"]),
        "badge": localize_badge(mod.get("badge", "Baza"), selected_lang),
        "duration_min": mod.get("duration_min", 15),
        "steps": steps,
        "common_mistakes": mistakes,
        "disqualification_trap": trap,
        "is_completed": is_done
    }
