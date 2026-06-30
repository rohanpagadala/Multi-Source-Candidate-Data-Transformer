import os
from typing import List, Dict, Any, Optional
from src.models import RawFact, CanonicalProfile
from src.extractors.resume import ResumeExtractor
from src.extractors.notes import NotesExtractor
from src.extractors.ats import ATSExtractor
from src.extractors.csv_export import CSVExtractor
from src.extractors.linkedin import LinkedInExtractor
from src.extractors.github import GitHubExtractor

from src.normalization import (
    normalize_email, normalize_phone, normalize_skill, 
    normalize_date, normalize_country
)
from src.merge import cluster_facts_by_candidate, merge_candidate_facts
from src.confidence import compute_profile_confidence
from src.projection import project_profile
from src.validation import validate_projected_output

ALL_EXTRACTORS = [
    ResumeExtractor(),
    NotesExtractor(),
    ATSExtractor(),
    CSVExtractor(),
    LinkedInExtractor(),
    GitHubExtractor()
]

def normalize_raw_facts(facts: List[RawFact]) -> List[RawFact]:
    """Normalize the raw facts field values before merging."""
    normalized_facts = []
    for fact in facts:
        val = fact.value
        field = fact.field
        
        if field == "email":
            val = normalize_email(str(val))
        elif field == "phone":
            val = normalize_phone(str(val))
        elif field == "skill":
            val = normalize_skill(str(val))
        elif field == "experience_item" and isinstance(val, dict):
            # Normalize dates in experience items
            val = {
                "company": val.get("company", ""),
                "title": val.get("title", ""),
                "start": normalize_date(val.get("start")),
                "end": normalize_date(val.get("end")),
                "summary": val.get("summary", "")
            }
        elif field == "education_item" and isinstance(val, dict):
            val = {
                "institution": val.get("institution", ""),
                "degree": val.get("degree"),
                "field": val.get("field"),
                "end_year": normalize_date(val.get("end_year"))  # YYYY-MM or YYYY
            }
            if val["end_year"] and len(val["end_year"]) > 4:
                val["end_year"] = val["end_year"][:4]  # Keep only year
                
        if val is not None:
            normalized_facts.append(RawFact(
                field=field,
                value=val,
                source=fact.source,
                method=fact.method,
                confidence=fact.confidence
            ))
            
    return normalized_facts

def run_pipeline(input_files: List[str], config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Runs the full end-to-end processing pipeline:
    Detect -> Extract -> Normalize -> Merge -> Confidence -> Project -> Validate.
    """
    raw_facts: List[RawFact] = []
    
    # 1. Detect & Extract Raw Facts
    for file_path in input_files:
        if not os.path.exists(file_path):
            print(f"Warning: File not found: {file_path}")
            continue
            
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
        except Exception as e:
            print(f"Warning: Error reading file {file_path}: {e}")
            continue
            
        extractor_found = False
        for extractor in ALL_EXTRACTORS:
            if extractor.can_extract(file_path, content):
                extractor_found = True
                try:
                    facts = extractor.extract(file_path, content)
                    raw_facts.extend(facts)
                except Exception as e:
                    print(f"Warning: Extractor {extractor.__class__.__name__} failed for {file_path}: {e}")
                break
                
        if not extractor_found:
            print(f"Warning: No matching extractor found for file: {file_path}")

    if not raw_facts:
        print("No raw facts extracted. Returning empty list.")
        return []

    # 2. Normalize Facts
    normalized_facts = normalize_raw_facts(raw_facts)

    # 3. Merge Facts into candidate clusters
    candidate_clusters = cluster_facts_by_candidate(normalized_facts)
    
    projected_profiles = []
    
    for cluster in candidate_clusters:
        # Merge group into profile
        profile = merge_candidate_facts(cluster)
        
        # 4. Confidence Scorer
        profile = compute_profile_confidence(profile)
        
        # 5. Project & Reshape according to runtime config
        projected = project_profile(profile, config or {})
        
        # 6. Schema check / validation
        validated = validate_projected_output(projected, config)
        
        projected_profiles.append(validated)
        
    return projected_profiles
