from typing import List
from src.models import CanonicalProfile, Skill, ProvenanceRecord
from src.merge import get_source_type

def get_source_reliability(source: str) -> float:
    stype = get_source_type(source)
    if stype in ["resume", "ats"]:
        return 1.0
    if stype in ["linkedin", "github"]:
        return 0.75
    if stype in ["notes"]:
        return 0.5
    return 1.0

def get_method_certainty(method: str) -> float:
    if "field" in method or "regex" in method or "first_line" in method or "label" in method:
        return 1.0
    if "keyword" in method or "phrase" in method or "bio" in method:
        return 0.7
    return 0.8

def calculate_fact_confidence(source: str, method: str) -> float:
    return get_source_reliability(source) * get_method_certainty(method)

def compute_profile_confidence(profile: CanonicalProfile) -> CanonicalProfile:
    """
    Computes field-level and overall confidence scores for the profile,
    applying corroboration boosts where a value is verified across multiple sources.
    """
    for skill in profile.skills:
        sources = set(skill.sources)
        base_conf = skill.confidence
    
        boost = 0.1 * (len(sources) - 1)
        skill.confidence = min(base_conf + boost, 1.0)
    provenance_by_field = {}
    for p in profile.provenance:
        if p.field not in provenance_by_field:
            provenance_by_field[p.field] = []
        provenance_by_field[p.field].append(p)

    field_confidences = []
    name_facts = provenance_by_field.get("full_name", [])
    if name_facts:
        max_conf = max(f.confidence for f in name_facts)
        unique_sources = {f.source for f in name_facts}
        boost = 0.1 * (len(unique_sources) - 1)
        name_conf = min(max_conf + boost, 1.0)
        field_confidences.append(name_conf)

    email_facts = provenance_by_field.get("emails", [])
    if email_facts:
        max_conf = max(f.confidence for f in email_facts)
        unique_sources = {f.source for f in email_facts}
        boost = 0.1 * (len(unique_sources) - 1)
        field_confidences.append(min(max_conf + boost, 1.0))

    phone_facts = provenance_by_field.get("phones", [])
    if phone_facts:
        max_conf = max(f.confidence for f in phone_facts)
        unique_sources = {f.source for f in phone_facts}
        boost = 0.1 * (len(unique_sources) - 1)
        field_confidences.append(min(max_conf + boost, 1.0))

    loc_facts = provenance_by_field.get("location", [])
    if loc_facts:
        max_conf = max(f.confidence for f in loc_facts)
        field_confidences.append(max_conf)

    headline_facts = provenance_by_field.get("headline", [])
    if headline_facts:
        max_conf = max(f.confidence for f in headline_facts)
        field_confidences.append(max_conf)

    exp_facts = provenance_by_field.get("experience", [])
    if exp_facts:
        max_conf = max(f.confidence for f in exp_facts)
        field_confidences.append(max_conf)

    edu_facts = provenance_by_field.get("education", [])
    if edu_facts:
        max_conf = max(f.confidence for f in edu_facts)
        field_confidences.append(max_conf)

    if profile.skills:
        avg_skills_conf = sum(s.confidence for s in profile.skills) / len(profile.skills)
        field_confidences.append(avg_skills_conf)

    if field_confidences:
        profile.overall_confidence = round(sum(field_confidences) / len(field_confidences), 2)
    else:
        profile.overall_confidence = 0.0

    return profile
