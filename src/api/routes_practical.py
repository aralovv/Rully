"""
Practical Driving Exam (Amaliy Imtihon) API endpoints for RULLY Mini App.
Provides curriculum modules, official checklist, and situational driving scenarios.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.deps import get_current_user, get_db
from src.bot.database import BotDatabase
from src.amaliy_curriculum import PRACTICAL_MODULES, PRACTICAL_CHECKLIST, PRACTICAL_SCENARIOS

router = APIRouter(prefix="/api/amaliy", tags=["Practical Exam"])

def get_valid_lang(lang: Optional[str], default_lang: str = "uz_latn") -> str:
    if lang in ["uz_latn", "uz_cyrl", "ru"]:
        return lang
    if default_lang in ["uz_latn", "uz_cyrl", "ru"]:
        return default_lang
    return "uz_latn"

# 1. Modules List
@router.get("/modules")
async def list_modules(
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
            "badge": m.get("badge", "Baza"),
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
async def toggle_module(
    req: ModuleToggleRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    new_state = db.toggle_completed_module(user["user_id"], req.module_id)
    return {"ok": True, "module_id": req.module_id, "is_completed": new_state}

# 2. Module Detail
@router.get("/modules/{module_id}")
async def get_module_detail(
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
        "badge": mod.get("badge", "Baza"),
        "duration_min": mod.get("duration_min", 15),
        "steps": steps,
        "common_mistakes": mistakes,
        "disqualification_trap": trap,
        "is_completed": is_done
    }

# 3. Official Autodrome & City Readiness Checklist
@router.get("/checklist")
async def get_checklist(
    lang: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    user_id = user["user_id"]
    selected_lang = get_valid_lang(lang, user.get("language", "uz_latn"))
    user_status = db.get_checklist_status(user_id)

    items = []
    completed_count = 0
    for chk in PRACTICAL_CHECKLIST:
        is_done = user_status.get(chk["id"], False)
        if is_done:
            completed_count += 1
        items.append({
            "id": chk["id"],
            "category": chk["category"],
            "title": chk["title"].get(selected_lang, chk["title"]["uz_latn"]),
            "is_completed": is_done
        })

    total = len(items)
    percentage = round((completed_count / total * 100), 1) if total > 0 else 0.0

    return {
        "language": selected_lang,
        "total": total,
        "completed_count": completed_count,
        "readiness_percentage": percentage,
        "items": items
    }

class ChecklistToggleRequest(BaseModel):
    item_id: str
    is_completed: Optional[bool] = None

@router.post("/checklist/toggle")
async def toggle_checklist(
    req: ChecklistToggleRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    new_state = db.toggle_checklist_item(user["user_id"], req.item_id, req.is_completed)
    return {"ok": True, "item_id": req.item_id, "is_completed": new_state}

@router.post("/checklist/reset")
async def reset_checklist(
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    db.reset_checklist(user["user_id"])
    return {"ok": True}

# 4. Situational Decision Tests
@router.get("/scenarios")
async def get_scenarios(
    lang: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user)
):
    selected_lang = get_valid_lang(lang, user.get("language", "uz_latn"))
    scenarios = []
    for s in PRACTICAL_SCENARIOS:
        opts = [
            {
                "id": opt["id"],
                "text": opt["text"].get(selected_lang, opt["text"]["uz_latn"])
            }
            for opt in s["options"]
        ]
        scenarios.append({
            "id": s["id"],
            "title": s["title"].get(selected_lang, s["title"]["uz_latn"]),
            "situation": s["situation"].get(selected_lang, s["situation"]["uz_latn"]),
            "options": opts
        })
    return {
        "language": selected_lang,
        "count": len(scenarios),
        "scenarios": scenarios
    }

class ScenarioAnswerRequest(BaseModel):
    scenario_id: str
    selected_option: int
    language: Optional[str] = None

@router.post("/scenarios/answer")
async def answer_scenario(
    req: ScenarioAnswerRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    db: BotDatabase = Depends(get_db)
):
    user_id = user["user_id"]
    selected_lang = get_valid_lang(req.language, user.get("language", "uz_latn"))
    scen = next((s for s in PRACTICAL_SCENARIOS if s["id"] == req.scenario_id), None)
    if not scen:
        raise HTTPException(status_code=404, detail="Scenario not found")

    correct_option = scen["correct_option"]
    is_correct = (req.selected_option == correct_option)

    # Persist in DB
    db.record_practical_quiz_result(
        user_id=user_id,
        scenario_id=req.scenario_id,
        selected_option=req.selected_option,
        is_correct=is_correct
    )

    return {
        "scenario_id": req.scenario_id,
        "selected_option": req.selected_option,
        "correct_option": correct_option,
        "is_correct": is_correct,
        "explanation": scen["explanation"].get(selected_lang, scen["explanation"]["uz_latn"])
    }
