"""
Canonical Image Scene Passport Normalizer.
Unifies all 17 historical schema typo variants in data/image_scenes.json into a single
strict 11-key canonical schema with uniform participant objects.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

CANONICAL_SCENE_KEYS = (
    "canonical_id",
    "filename",
    "category_name",
    "sahna_turi",
    "vizual_muhit_va_yo‘l",
    "belgilar_va_chiziqlar",
    "tartibga_soluvchi_yoki_svetofor",
    "ishtirokchilar_va_obyektlar",
    "traektoriyalar_tahlili",
    "otish_tartibi_yoki_yechim",
    "yhq_qoidasi_va_asos",
)

CANONICAL_PARTICIPANT_KEYS = (
    "obyekt",
    "joylashuvi",
    "harakat_yonalishi_yoki_traektoriya",
    "holati_va_huquqi",
)


def _first_non_empty(d: Dict[str, Any], keys: Tuple[str, ...], default: Any = "") -> Any:
    for k in keys:
        val = d.get(k)
        if val is not None and (not isinstance(val, str) or val.strip()):
            return val
    return default


def normalize_participant(raw: Any) -> Dict[str, str]:
    if not isinstance(raw, dict):
        return {k: str(raw or "") if k == "obyekt" else "" for k in CANONICAL_PARTICIPANT_KEYS}
    return {
        "obyekt": str(_first_non_empty(raw, ("obyekt", "mashina", "transport", "name"), "Transport vositasi")).strip(),
        "joylashuvi": str(_first_non_empty(raw, ("joylashuvi", "position"), "")).strip(),
        "harakat_yonalishi_yoki_traektoriya": str(
            _first_non_empty(
                raw,
                ("harakat_yonalishi_yoki_traektoriya", "harakat_yonalishi", "yonalish", "traektoriya"),
                "",
            )
        ).strip(),
        "holati_va_huquqi": str(
            _first_non_empty(raw, ("holati_va_huquqi", "holati", "huquqi"), "")
        ).strip(),
    }


def normalize_scene_entry(filename_key: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    """Converts any legacy/typo image scene object into the strict canonical schema."""
    solution_val = _first_non_empty(raw, ("otish_tartibi_yoki_yechim", "otish_ketmaketligi"), "")
    if not solution_val:
        for k, v in raw.items():
            if k.startswith("otish_tartibi_") and isinstance(v, str) and v.strip():
                solution_val = v.strip()
                break

    reg_val = _first_non_empty(
        raw,
        (
            "tartibga_soluvchi_yoki_svetofor",
            "tartibga_soluvch_yoki_svetofor",
            "tartibga_soluvchi_yoki_tartibga_soluvchi_va_svetofor",
        ),
        "Mavjud emas",
    )

    raw_participants = raw.get("ishtirokchilar_va_obyektlar")
    if raw_participants is None:
        raw_participants = raw.get("transport_vositalari")
    participants: List[Dict[str, str]] = (
        [normalize_participant(p) for p in raw_participants]
        if isinstance(raw_participants, list)
        else []
    )

    return {
        "canonical_id": str(raw.get("canonical_id") or "").strip(),
        "filename": str(raw.get("filename") or filename_key).strip(),
        "category_name": str(raw.get("category_name") or "").strip(),
        "sahna_turi": str(_first_non_empty(raw, ("sahna_turi", "vaziyat_turi"), "Yo‘l vaziyati")).strip(),
        "vizual_muhit_va_yo‘l": str(
            _first_non_empty(raw, ("vizual_muhit_va_yo‘l", "vizual_muhit_va_yo'l"), "")
        ).strip(),
        "belgilar_va_chiziqlar": str(raw.get("belgilar_va_chiziqlar") or "").strip(),
        "tartibga_soluvchi_yoki_svetofor": str(reg_val).strip(),
        "ishtirokchilar_va_obyektlar": participants,
        "traektoriyalar_tahlili": str(raw.get("traektoriyalar_tahlili") or "Mavjud emas").strip(),
        "otish_tartibi_yoki_yechim": str(solution_val).strip(),
        "yhq_qoidasi_va_asos": str(_first_non_empty(raw, ("yhq_qoidasi_va_asos", "qoida_asosi"), "")).strip(),
    }


def normalize_image_scenes_file(json_path: str = "data/image_scenes.json") -> Dict[str, Any]:
    path = Path(json_path)
    raw_data = json.loads(path.read_text(encoding="utf-8"))
    normalized: Dict[str, Dict[str, Any]] = {}
    with_solution = 0

    for outer_key, entry in raw_data.items():
        if not isinstance(entry, dict):
            continue
        fname = str(entry.get("filename") or outer_key)
        clean_entry = normalize_scene_entry(fname, entry)
        if clean_entry["otish_tartibi_yoki_yechim"]:
            with_solution += 1
        target_key = clean_entry.get("canonical_id") or outer_key
        normalized[target_key] = clean_entry

    tmp_path = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)

    return {
        "total_entries": len(normalized),
        "solutions_non_empty": with_solution,
        "distinct_key_schemas": len({tuple(sorted(v.keys())) for v in normalized.values()}),
    }
