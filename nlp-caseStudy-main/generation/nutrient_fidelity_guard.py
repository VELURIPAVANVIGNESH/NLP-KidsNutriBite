"""
generation/nutrient_fidelity_guard.py - NutriKid GEN001 Fix: Nutrient Fidelity Guard

Lightweight DETERMINISTIC post-generation validation layer.

Checks:
  1. Requested nutrient matches the nutrient discussed in the generated answer.
  2. Numerical values use units compatible with the requested nutrient.
  3. Cross-nutrient unit contamination (e.g. microg/day for protein) is rejected.

Priority: INSUFFICIENT EVIDENCE > HALLUCINATION > WRONG NUTRIENT SUBSTITUTION

This is a safety/fidelity engineering guard, NOT a medical diagnosis system.
"""

import re
from typing import Optional

# Each entry: (expected_unit patterns, forbidden_unit patterns, expected_kw, forbidden_nutrient_kw)
_NUTRIENT_UNIT_RULES = {
    "protein": {
        "expected_units": [r"\bg/day\b", r"\bgrams?\b", r"\bg\s*/\s*day\b"],
        "forbidden_units": [
            # spelled-out forms
            r"\bmicrograms?\s*/\s*day\b",
            r"\bmicrograms?\b",
            # unicode µg symbol
            r"\bµg\s*/\s*day\b",
            r"\bµg\b",
            # ascii ug abbreviation (case-insensitive via re.IGNORECASE)
            r"\bug\s*/\s*day\b",
            r"\bug\b",
            r"\bpg/day\b",
        ],
        "expected_keywords": ["protein"],
        "forbidden_nutrient_keywords": ["iodine", "iodised", "iodized", "thyroid"],
    },
    "calcium": {
        "expected_units": [r"\bmg/day\b", r"\bmilligrams?/day\b"],
        "forbidden_units": [
            r"\bmicrograms?\s*/\s*day\b",
            r"\bµg\s*/\s*day\b",
            r"\bµg\b",
            r"\bug\s*/\s*day\b",
        ],
        "expected_keywords": ["calcium"],
        "forbidden_nutrient_keywords": [],
    },
    "iron": {
        "expected_units": [r"\bmg/day\b", r"\bmilligrams?/day\b"],
        "forbidden_units": [
            r"\bmicrograms?\s*/\s*day\b",
            r"\bµg\s*/\s*day\b",
            r"\bµg\b",
            r"\bug\s*/\s*day\b",
        ],
        "expected_keywords": ["iron"],
        "forbidden_nutrient_keywords": [],
    },
    "sodium": {
        "expected_units": [r"\bmg/day\b", r"\bg/day\b"],
        "forbidden_units": [
            r"\bmicrograms?\s*/\s*day\b",
            r"\bµg\s*/\s*day\b",
            r"\bµg\b",
            r"\bug\s*/\s*day\b",
        ],
        "expected_keywords": ["sodium", "salt"],
        "forbidden_nutrient_keywords": [],
    },
    "sugar": {
        "expected_units": [r"\bg/day\b", r"\benergy\b"],
        "forbidden_units": [
            r"\bmicrograms?\s*/\s*day\b",
            r"\bµg\s*/\s*day\b",
            r"\bµg\b",
            r"\bug\s*/\s*day\b",
        ],
        "expected_keywords": ["sugar", "free sugar"],
        "forbidden_nutrient_keywords": [],
    },
    "vitamin a": {
        "expected_units": [r"\bµg/day\b", r"\bug/day\b", r"\bmicrograms?\b", r"\bµg RE\b", r"\bRE\b", r"\bµg\b"],
        "forbidden_units": [r"\bg/day\b"],
        "expected_keywords": ["vitamin a", "retinol"],
        "forbidden_nutrient_keywords": [],
    },
}

_NUTRIENT_ALIASES = {
    "vitamin a": "vitamin a",
    "protein": "protein",
    "proteins": "protein",
    "calcium": "calcium",
    "iron": "iron",
    "sodium": "sodium",
    "salt": "sodium",
    "sugar": "sugar",
    "sugars": "sugar",
    "free sugar": "sugar",
}


def detect_requested_nutrient(query: str) -> Optional[str]:
    """Infer primary nutrient from query. Returns canonical key or None."""
    q_lower = query.lower()
    for alias, canonical in _NUTRIENT_ALIASES.items():
        if alias in q_lower:
            return canonical
    return None


def _has_forbidden_unit_without_expected(answer: str, nutrient_key: str) -> bool:
    """
    True if answer contains forbidden units for the nutrient AND
    does NOT contain any expected units for that nutrient.
    """
    rules = _NUTRIENT_UNIT_RULES.get(nutrient_key)
    if rules is None:
        return False
    forbidden_units = rules.get("forbidden_units", [])
    expected_units = rules.get("expected_units", [])
    has_forbidden = any(re.search(p, answer, re.IGNORECASE) for p in forbidden_units)
    if not has_forbidden:
        return False
    has_expected = any(re.search(p, answer, re.IGNORECASE) for p in expected_units)
    return not has_expected


def _has_forbidden_nutrient_keyword(answer: str, nutrient_key: str) -> bool:
    """True if answer discusses wrong nutrient AND does NOT discuss requested nutrient."""
    rules = _NUTRIENT_UNIT_RULES.get(nutrient_key)
    if rules is None:
        return False
    forbidden_kw = rules.get("forbidden_nutrient_keywords", [])
    expected_kw = rules.get("expected_keywords", [])
    if not any(kw in answer.lower() for kw in forbidden_kw):
        return False
    return not any(kw in answer.lower() for kw in expected_kw)


def validate_nutrient_fidelity(query: str, answer: str) -> dict:
    """
    Main entry point for nutrient fidelity validation.

    Returns dict with keys:
        passed, nutrient_detected, unit_contaminated,
        nutrient_contaminated, failure_reason, method
    """
    nutrient_key = detect_requested_nutrient(query)
    result = {
        "passed": True,
        "nutrient_detected": nutrient_key or "unknown",
        "unit_contaminated": False,
        "nutrient_contaminated": False,
        "failure_reason": "",
        "explanation": "",
        "method": "deterministic_fidelity_guard",
    }
    if nutrient_key is None:
        return result  # Cannot validate unknown nutrient - pass through

    if _has_forbidden_unit_without_expected(answer, nutrient_key):
        result["passed"] = False
        result["unit_contaminated"] = True
        result["failure_reason"] = (
            "UNIT CONTAMINATION: Answer contains units incompatible with "
            + repr(nutrient_key)
            + ". For protein, expected g/day but found microgram-scale units "
            "(micrograms/day, µg/day, or ug/day). "
            "Returning evidence-insufficient response."
        )
        result["explanation"] = result["failure_reason"]
        return result

    if _has_forbidden_nutrient_keyword(answer, nutrient_key):
        result["passed"] = False
        result["nutrient_contaminated"] = True
        result["failure_reason"] = (
            "NUTRIENT CONTAMINATION: Answer discusses wrong nutrient instead of "
            + repr(nutrient_key) + "."
        )
        result["explanation"] = result["failure_reason"]
        return result

    return result


def apply_fidelity_guard(
    query: str, child_age, answer: str, citations: list, generation_metadata: dict
) -> dict:
    """
    Wrap generated answer with fidelity validation.
    If validation fails, replaces answer with evidence-insufficient notice.

    Returns dict: answer, citations, generation_metadata, fidelity_check
    """
    fidelity = validate_nutrient_fidelity(query, answer)

    if fidelity["passed"]:
        return {
            "answer": answer,
            "citations": citations,
            "generation_metadata": generation_metadata,
            "fidelity_check": fidelity,
        }

    nutrient = fidelity["nutrient_detected"]
    age_str = (
        "a {}-year-old child".format(child_age)
        if child_age is not None
        else "the requested child"
    )
    insufficient = (
        "Nutrient Fidelity Guard triggered.\n\n"
        + fidelity["failure_reason"]
        + "\n\nThe supplied evidence does not provide a specific "
        + nutrient
        + " recommendation for "
        + age_str
        + ". The retrieved passages appear to cover a different nutrient. "
        "Please consult official ICMR-NIN 2020 or WHO guidelines directly."
    )
    return {
        "answer": insufficient,
        "citations": [],
        "generation_metadata": generation_metadata,
        "fidelity_check": fidelity,
    }
