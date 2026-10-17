"""
generation/domain_guard.py — NutriKid Domain Scope Guardrail

Enforces domain boundary: NutriKid is an evidence-grounded clinical system
strictly specialized in pediatric nutrition, dietary guidelines, nutrients,
and food requirements for children (ages 5.0–15.0 years).

Rejects out-of-domain queries (sports, entertainment, politics, coding,
general trivia, non-nutrition topics) immediately before retrieval or generation.
"""

import re
from typing import Tuple

# Explicit out-of-domain keyword patterns (sports, entertainment, politics, programming, trivia)
_OUT_OF_DOMAIN_PATTERNS = [
    # Sports & games
    r"\b(cricket|football|soccer|basketball|tennis|badminton|hockey|baseball|rugby|volleyball)\b",
    r"\b(ipl|bcci|fifa|icc|nba|epl|olympics|world\s*cup)\b",
    r"\b(match\s*summary|scorecard|wicket|wickets|batsman|bowler|batting|bowling|stadium)\b",
    r"\b(runs\s*scored|toss|overs|innings|penalty|goal\s*scorer|championship)\b",
    
    # Entertainment & media
    r"\b(movie|movies|cinema|film|films|actor|actress|bollywood|hollywood)\b",
    r"\b(song|songs|music|lyrics|singer|album|box\s*office|trailer|netflix|actor|cinema)\b",
    
    # Politics & governance
    r"\b(politics|election|elections|parliament|prime\s*minister|president)\b",
    r"\b(minister|political\s*party|bjp|congress|democrat|republican|war|military|army)\b",
    
    # Technology & programming
    r"\b(python|javascript|typescript|java|c\+\+|html|css|sql|github|programming|coding)\b",
    r"\b(algorithm|source\s*code|debug|compile|software|app\s*development|binary\s*search)\b",
    
    # Financial markets & general non-nutrition trivia
    r"\b(stock\s*market|cryptocurrency|crypto|bitcoin|ethereum|forex|share\s*price)\b",
    r"\b(capital\s+of|weather\s+forecast|horoscope|astrology|flight\s+ticket|car\s+price|black\s*holes?)\b",
]

# In-domain clinical nutrition, food, nutrient, and pediatric health patterns
_IN_DOMAIN_PATTERNS = [
    # Specific nutrients & biochemical markers
    r"\b(protein|proteins|calcium|iron|zinc|sodium|potassium|iodine|folate|folic\s*acid)\b",
    r"\b(vitamin|vitamins|mineral|minerals|nutrient|nutrients|macronutrient|macronutrients|micronutrient|micronutrients)\b",
    r"\b(carbohydrate|carbohydrates|carb|carbs|fat|fats|lipid|lipids|fiber|fibre|sugar|sugars)\b",
    r"\b(calorie|calories|kcal|energy|amino\s*acid|fatty\s*acid|water|hydration|electrolyte)\b",
    
    # Dietary metrics, allowances, guidelines & institutions
    r"\b(rda|ear|ul|tul|recommended\s*dietary\s*allowance|estimated\s*average\s*requirement|upper\s*limit)\b",
    r"\b(diet|dietary|dietitian|nutrition|nutritional|intake|requirement|requirements|allowance|allowances)\b",
    r"\b(deficiency|deficiencies|excess|toxicity|supplement|supplements|balanced\s*diet)\b",
    r"\b(icmr|nin|fao|ifct|unicef|poshan|dietary\s*guidelines?|world\s+health\s+organization|who\s+guidelines?)\b",
    
    # Food items, meals, eating & digestion
    r"\b(food|foods|meal|meals|feed|feeding|eat|eating|snack|snacks|breakfast|lunch|dinner)\b",
    r"\b(milk|dairy|egg|eggs|curd|yogurt|paneer|cheese|meat|poultry|fish|chicken)\b",
    r"\b(vegetable|vegetables|fruit|fruits|grain|grains|pulse|pulses|dal|cereal|cereals|rice|wheat|millet)\b",
    r"\b(portion|servings?|portion\s*size|recipe|nutrition\s*chart|food\s*pyramid)\b",
    
    # Pediatric & child health contexts
    r"\b(pediatric|pediatrics|infant|infants|toddler|toddlers|adolescent|adolescents|puberty)\b",
    r"\b(stunting|wasting|underweight|overweight|obesity|malnutrition|undernutrition|anemia|scurvy|rickets)\b",
]

def validate_domain_scope(query: str) -> Tuple[bool, str]:
    """
    Validates whether a user query falls within the NutriKid Pediatric Clinical Nutrition scope.
    
    Returns:
        (is_valid: bool, refusal_reason: str)
    """
    q = query.strip()
    if not q:
        return False, "Out of Domain Notice: Empty query received."
    
    # 1. Check uppercase WHO or in-domain patterns
    has_who = bool(re.search(r"\bWHO\b", q))
    has_in_domain = has_who or any(re.search(pat, q, re.I) for pat in _IN_DOMAIN_PATTERNS)
    
    # 2. Check explicit out-of-domain patterns
    has_out_of_domain = any(re.search(pat, q, re.I) for pat in _OUT_OF_DOMAIN_PATTERNS)
    
    # If out-of-domain topic and not asking about nutrition -> Refuse
    if has_out_of_domain and not has_in_domain:
        return False, (
            f"Out of Domain Notice: NutriKid is an evidence-grounded clinical assistant specialized strictly in "
            f"pediatric nutrition and dietary guidelines for children (ages 5.0 to 15.0 years).\n\n"
            f"Your question ('{q}') is outside the clinical nutrition domain. NutriKid does not provide sports, "
            f"entertainment, coding, politics, or general media information.\n\n"
            f"Please ask a question related to pediatric nutrition, such as dietary allowances (RDA/EAR), "
            f"vitamins, minerals, energy requirements, or food guidelines for children."
        )
    
    # If query has zero nutrition/food/health context -> Refuse
    if not has_in_domain:
        return False, (
            f"Out of Domain Notice: NutriKid is specialized strictly in pediatric nutrition and dietary guidelines for children (ages 5.0 to 15.0 years).\n\n"
            f"Your question ('{q}') does not appear to reference nutrition, dietary requirements, vitamins, minerals, or child dietary health.\n\n"
            f"Please rephrase your question to include the relevant nutrient, food item, or dietary guideline (e.g., protein RDA, calcium requirements, vitamin intake)."
        )
    
    return True, ""
