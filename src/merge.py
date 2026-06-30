import re
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
from src.models import RawFact, CanonicalProfile, Location, Links, Skill, Experience, Education, ProvenanceRecord
from src.normalization import (
    normalize_email, normalize_phone, normalize_date, 
    normalize_country, normalize_skill, parse_location
)

SOURCE_PRIORITY = {
    "resume": 3,
    "ats": 3,
    "linkedin": 2,
    "github": 2,
    "notes": 1
}

def get_source_type(source: str) -> str:
    name = source.lower()
    if "resume" in name:
        return "resume"
    if "ats" in name:
        return "ats"
    if "linkedin" in name:
        return "linkedin"
    if "github" in name:
        return "github"
    if "notes" in name or "recruiter" in name:
        return "notes"
    return "resume"

def get_priority(source: str) -> int:
    return SOURCE_PRIORITY.get(get_source_type(source), 1)

def cluster_facts_by_candidate(facts: List[RawFact]) -> List[List[RawFact]]:
    """
    Cluster facts by candidate. Uses email or phone exact match.
    Falls back to normalized name matching if no contact info exists.
    """
    # 1. Group facts by their source file
    facts_by_source: Dict[str, List[RawFact]] = defaultdict(list)
    for fact in facts:
        facts_by_source[fact.source].append(fact)

    # 2. Extract identity keys for each source file
    source_keys: Dict[str, Dict[str, Any]] = {}
    for src, src_facts in facts_by_source.items():
        emails = set()
        phones = set()
        name = ""
        for f in src_facts:
            if f.field == "email":
                e = normalize_email(f.value)
                if e:
                    emails.add(e)
            elif f.field == "phone":
                p = normalize_phone(f.value)
                if p:
                    phones.add(p)
            elif f.field == "full_name":
                name = f.value.strip().lower()
        source_keys[src] = {"emails": emails, "phones": phones, "name": name}

    # 3. Cluster source files using Union-Find or simple grouping
    parent: Dict[str, str] = {src: src for src in facts_by_source}

    def find(i: str) -> str:
        path = []
        while parent[i] != i:
            path.append(i)
            i = parent[i]
        for node in path:
            parent[node] = i
        return i

    def union(i: str, j: str):
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    src_list = list(facts_by_source.keys())
    
    # First pass: Link by Email or Phone
    for i in range(len(src_list)):
        for j in range(i + 1, len(src_list)):
            src_i, src_j = src_list[i], src_list[j]
            keys_i, keys_j = source_keys[src_i], source_keys[src_j]
            
            # Match by emails
            if keys_i["emails"] & keys_j["emails"]:
                union(src_i, src_j)
                continue
                
            # Match by phones
            if keys_i["phones"] & keys_j["phones"]:
                union(src_i, src_j)
                continue

    # Second pass: Fallback to Name-based matching if one or both have NO contact info
    for i in range(len(src_list)):
        for j in range(i + 1, len(src_list)):
            src_i, src_j = src_list[i], src_list[j]
            if find(src_i) == find(src_j):
                continue
                
            keys_i, keys_j = source_keys[src_i], source_keys[src_j]
            
            # If name matches exactly (normalized space) and at least one has no emails/phones
            name_i = re.sub(r'\s+', ' ', keys_i["name"]).strip()
            name_j = re.sub(r'\s+', ' ', keys_j["name"]).strip()
            if name_i and name_i == name_j:
                no_contact_i = not keys_i["emails"] and not keys_i["phones"]
                no_contact_j = not keys_j["emails"] and not keys_j["phones"]
                if no_contact_i or no_contact_j:
                    union(src_i, src_j)

    # 4. Gather facts for each candidate cluster
    clusters: Dict[str, List[RawFact]] = defaultdict(list)
    for src, src_facts in facts_by_source.items():
        root = find(src)
        clusters[root].extend(src_facts)

    return list(clusters.values())

def merge_candidate_facts(candidate_facts: List[RawFact]) -> CanonicalProfile:
    """Merge facts of a single candidate into a CanonicalProfile."""
    # Group facts by field type
    facts_by_field: Dict[str, List[RawFact]] = defaultdict(list)
    for fact in candidate_facts:
        facts_by_field[fact.field].append(fact)

    provenance: List[ProvenanceRecord] = []
    
    # Helper to resolve scalar field values based on source priority and confidence
    def resolve_scalar(field_name: str, default_val: Any) -> Tuple[Any, float]:
        field_facts = facts_by_field.get(field_name, [])
        if not field_facts:
            return default_val, 0.0
            
        # Sort facts by:
        # 1. Source priority (highest first)
        # 2. Fact confidence (highest first)
        sorted_facts = sorted(
            field_facts,
            key=lambda x: (get_priority(x.source), x.confidence),
            reverse=True
        )
        
        winner = sorted_facts[0]
        
        # Record all facts (winner and losers) in provenance
        for f in field_facts:
            # Losers are stored at a discounted confidence score (discounted by 30%)
            is_winner = (f == winner)
            conf = f.confidence if is_winner else f.confidence * 0.7
            provenance.append(ProvenanceRecord(
                field=field_name,
                source=f.source,
                method=f.method,
                confidence=conf,
                value=f.value
            ))
            
        return winner.value, winner.confidence

    # 1. Candidate ID: generated from name or email hash
    emails_raw = [f.value for f in facts_by_field.get("email", [])]
    emails_norm = sorted(list({normalize_email(e) for e in emails_raw if normalize_email(e)}))
    
    name_val, name_conf = resolve_scalar("full_name", "")
    
    if emails_norm:
        cand_id = re.sub(r'[^a-zA-Z0-9]', '', emails_norm[0].split('@')[0])
    else:
        cand_id = re.sub(r'[^a-zA-Z0-9]', '', name_val.lower())
        
    # 2. Headline
    headline_val, headline_conf = resolve_scalar("headline", None)

    # 3. Location: merge city, region, country
    location_facts = facts_by_field.get("location", [])
    city, region, country = "", "", ""
    loc_winner_priority = -1
    loc_winner_conf = -1.0
    
    for f in location_facts:
        loc_dict = parse_location(f.value) if isinstance(f.value, str) else f.value
        priority = get_priority(f.source)
        # If this source is higher priority, use it
        if priority > loc_winner_priority or (priority == loc_winner_priority and f.confidence > loc_winner_conf):
            city = loc_dict.get("city", "")
            region = loc_dict.get("region", "")
            country = loc_dict.get("country", "")
            loc_winner_priority = priority
            loc_winner_conf = f.confidence
        
        provenance.append(ProvenanceRecord(
            field="location",
            source=f.source,
            method=f.method,
            confidence=f.confidence if (priority == loc_winner_priority) else f.confidence * 0.7,
            value=loc_dict
        ))
        
    location_obj = Location(city=city, region=region, country=country)

    # 4. Links: merge github, linkedin, portfolio, other
    github_val, _ = resolve_scalar("github_link", None)
    linkedin_val, _ = resolve_scalar("linkedin_link", None)
    portfolio_val, _ = resolve_scalar("portfolio_link", None)
    
    other_links = set()
    for f in facts_by_field.get("other_link", []):
        other_links.add(f.value)
        provenance.append(ProvenanceRecord(
            field="other_link",
            source=f.source,
            method=f.method,
            confidence=f.confidence,
            value=f.value
        ))
        
    links_obj = Links(
        linkedin=linkedin_val,
        github=github_val,
        portfolio=portfolio_val,
        other=sorted(list(other_links))
    )

    # 5. Emails and Phones (Arrays)
    phones_raw = [f.value for f in facts_by_field.get("phone", [])]
    phones_norm = sorted(list({normalize_phone(p) for p in phones_raw if normalize_phone(p)}))
    
    # Store email/phone facts in provenance
    for f in facts_by_field.get("email", []):
        provenance.append(ProvenanceRecord(
            field="emails", source=f.source, method=f.method, confidence=f.confidence, value=f.value
        ))
    for f in facts_by_field.get("phone", []):
        provenance.append(ProvenanceRecord(
            field="phones", source=f.source, method=f.method, confidence=f.confidence, value=f.value
        ))

    # 6. Skills (Array with confidence and sources union)
    skill_facts = facts_by_field.get("skill", [])
    skills_map: Dict[str, Dict[str, Any]] = {}
    for f in skill_facts:
        raw_skill = f.value
        norm_skill = normalize_skill(raw_skill)
        
        if norm_skill not in skills_map:
            skills_map[norm_skill] = {
                "name": norm_skill,
                "confidence": f.confidence,
                "sources": {f.source},
                "max_priority": get_priority(f.source)
            }
        else:
            skills_map[norm_skill]["sources"].add(f.source)
            # Update confidence if higher
            if f.confidence > skills_map[norm_skill]["confidence"]:
                skills_map[norm_skill]["confidence"] = f.confidence
            if get_priority(f.source) > skills_map[norm_skill]["max_priority"]:
                skills_map[norm_skill]["max_priority"] = get_priority(f.source)
                
        provenance.append(ProvenanceRecord(
            field="skills",
            source=f.source,
            method=f.method,
            confidence=f.confidence,
            value=raw_skill
        ))

    # 7. Experience (Union + De-duplication on normalized company & title)
    experience_facts = facts_by_field.get("experience_item", [])
    experience_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for f in experience_facts:
        val = f.value
        comp = val.get("company", "").strip()
        title = val.get("title", "").strip()
        
        # Simple key: lowercase alphanumeric only
        comp_key = re.sub(r'\W+', '', comp.lower())
        title_key = re.sub(r'\W+', '', title.lower())
        
        # Check if there is already an entry for this company to avoid placeholder duplicate
        matching_keys = [k for k in experience_map.keys() if k[0] == comp_key]
        if title_key == "employee" and matching_keys:
            key = matching_keys[0]
        elif matching_keys and any(k[1] == "employee" for k in matching_keys):
            # Rename existing placeholder key to the detailed key
            emp_key = next(k for k in matching_keys if k[1] == "employee")
            experience_map[(comp_key, title_key)] = experience_map.pop(emp_key)
            key = (comp_key, title_key)
        else:
            key = (comp_key, title_key)
        
        start_norm = normalize_date(val.get("start"))
        end_norm = normalize_date(val.get("end"))
        
        if key not in experience_map:
            experience_map[key] = {
                "company": comp,
                "title": title,
                "start": start_norm,
                "end": end_norm,
                "summary": val.get("summary", ""),
                "priority": get_priority(f.source),
                "confidence": f.confidence
            }
        else:
            # Overwrite dates/summary if this source is higher priority or has start date and existing doesn't
            existing = experience_map[key]
            current_priority = get_priority(f.source)
            if current_priority > existing["priority"]:
                existing["company"] = comp
                existing["title"] = title
                if start_norm:
                    existing["start"] = start_norm
                if end_norm:
                    existing["end"] = end_norm
                if val.get("summary"):
                    existing["summary"] = val.get("summary")
                existing["priority"] = current_priority
                existing["confidence"] = max(existing["confidence"], f.confidence)
            else:
                # Merge summaries if not identical
                if val.get("summary") and val.get("summary") not in existing["summary"]:
                    existing["summary"] += "\n" + val.get("summary")
                if not existing["start"] and start_norm:
                    existing["start"] = start_norm
                if not existing["end"] and end_norm:
                    existing["end"] = end_norm
                    
        provenance.append(ProvenanceRecord(
            field="experience",
            source=f.source,
            method=f.method,
            confidence=f.confidence,
            value=val
        ))

    experience_list = []
    for exp_val in experience_map.values():
        experience_list.append(Experience(
            company=exp_val["company"],
            title=exp_val["title"],
            start=exp_val["start"],
            end=exp_val["end"],
            summary=exp_val["summary"]
        ))

    # 8. Education (Union + De-duplication on normalized institution)
    education_facts = facts_by_field.get("education_item", [])
    education_map: Dict[str, Dict[str, Any]] = {}
    for f in education_facts:
        val = f.value
        inst = val.get("institution", "").strip()
        inst_clean = re.sub(r'\(.*?\)', '', inst).strip()
        inst_key = re.sub(r'\W+', '', inst_clean.lower())
        
        if inst_key not in education_map:
            education_map[inst_key] = {
                "institution": inst,
                "degree": val.get("degree"),
                "field": val.get("field"),
                "end_year": val.get("end_year"),
                "priority": get_priority(f.source),
                "confidence": f.confidence
            }
        else:
            existing = education_map[inst_key]
            current_priority = get_priority(f.source)
            if current_priority > existing["priority"]:
                existing["institution"] = inst
                if val.get("degree"):
                    existing["degree"] = val.get("degree")
                if val.get("field"):
                    existing["field"] = val.get("field")
                if val.get("end_year"):
                    existing["end_year"] = val.get("end_year")
                existing["priority"] = current_priority
                existing["confidence"] = max(existing["confidence"], f.confidence)
            else:
                if not existing.get("degree") and val.get("degree"):
                    existing["degree"] = val.get("degree")
                if not existing.get("field") and val.get("field"):
                    existing["field"] = val.get("field")
                if not existing.get("end_year") and val.get("end_year"):
                    existing["end_year"] = val.get("end_year")
                
        provenance.append(ProvenanceRecord(
            field="education",
            source=f.source,
            method=f.method,
            confidence=f.confidence,
            value=val
        ))

    education_list = []
    for edu_val in education_map.values():
        education_list.append(Education(
            institution=edu_val["institution"],
            degree=edu_val["degree"],
            field=edu_val["field"],
            end_year=edu_val["end_year"]
        ))

    # 9. Projects (Union + De-duplication on normalized project name)
    from src.models import Project, Certification
    
    project_facts = facts_by_field.get("project_item", [])
    project_map: Dict[str, Dict[str, Any]] = {}
    for f in project_facts:
        val = f.value
        name = val.get("name", "").strip()
        name_key = re.sub(r'\W+', '', name.lower())
        
        techs = val.get("technologies", [])
        if not isinstance(techs, list):
            techs = []
            
        if name_key not in project_map:
            project_map[name_key] = {
                "name": name,
                "description": val.get("description", ""),
                "link": val.get("link"),
                "technologies": set(techs),
                "priority": get_priority(f.source),
                "confidence": f.confidence
            }
        else:
            existing = project_map[name_key]
            existing["technologies"].update(techs)
            
            desc = val.get("description", "")
            if len(desc) > len(existing["description"]):
                existing["description"] = desc
                
            if val.get("link") and not existing["link"]:
                existing["link"] = val.get("link")
                
            current_priority = get_priority(f.source)
            if current_priority > existing["priority"]:
                existing["name"] = name
                existing["priority"] = current_priority
                existing["confidence"] = max(existing["confidence"], f.confidence)
                
        provenance.append(ProvenanceRecord(
            field="projects",
            source=f.source,
            method=f.method,
            confidence=f.confidence,
            value=val
        ))
        
    projects_list = []
    for proj_val in project_map.values():
        projects_list.append(Project(
            name=proj_val["name"],
            description=proj_val["description"],
            technologies=sorted(list(proj_val["technologies"]))
        ))

    # 10. Certifications (Union + De-duplication on normalized name)
    cert_facts = facts_by_field.get("certification_item", [])
    cert_map: Dict[str, Dict[str, Any]] = {}
    for f in cert_facts:
        val = f.value
        name = val.get("name", "").strip()
        name_key = re.sub(r'\W+', '', name.lower())
        
        if name_key not in cert_map:
            cert_map[name_key] = {
                "name": name,
                "issuing_organization": val.get("issuing_organization"),
                "year": val.get("year"),
                "priority": get_priority(f.source),
                "confidence": f.confidence
            }
        else:
            existing = cert_map[name_key]
            current_priority = get_priority(f.source)
            if current_priority > existing["priority"]:
                existing["name"] = name
                if val.get("issuing_organization"):
                    existing["issuing_organization"] = val.get("issuing_organization")
                if val.get("year"):
                    existing["year"] = val.get("year")
                existing["priority"] = current_priority
                existing["confidence"] = max(existing["confidence"], f.confidence)
            else:
                if not existing.get("issuing_organization") and val.get("issuing_organization"):
                    existing["issuing_organization"] = val.get("issuing_organization")
                if not existing.get("year") and val.get("year"):
                    existing["year"] = val.get("year")
                    
        provenance.append(ProvenanceRecord(
            field="certifications",
            source=f.source,
            method=f.method,
            confidence=f.confidence,
            value=val
        ))
        
    certifications_list = []
    for cert_val in cert_map.values():
        certifications_list.append(Certification(
            name=cert_val["name"],
            issuing_organization=cert_val["issuing_organization"],
            year=cert_val["year"]
        ))

    # 11. Years of Experience (Heuristic or direct field)
    years_exp_val, _ = resolve_scalar("years_experience", None)
    if years_exp_val is None:
        total_months = 0
        for exp in experience_list:
            if exp.start:
                start_match = re.match(r'^(\d{4})-(\d{2})$', exp.start)
                if start_match:
                    start_yr, start_m = map(int, start_match.groups())
                    end_yr, end_m = 2026, 12
                    if exp.end and exp.end != "Present":
                        end_match = re.match(r'^(\d{4})-(\d{2})$', exp.end)
                        if end_match:
                            end_yr, end_m = map(int, end_match.groups())
                    months = (end_yr - start_yr) * 12 + (end_m - start_m)
                    if months > 0:
                        total_months += months
        years_exp_val = round(total_months / 12.0, 1) if total_months > 0 else 0.0

    skills_list = []
    for skill_info in skills_map.values():
        skills_list.append(Skill(
            name=skill_info["name"],
            confidence=skill_info["confidence"],
            sources=sorted(list(skill_info["sources"]))
        ))

    profile = CanonicalProfile(
        candidate_id=cand_id,
        full_name=name_val,
        emails=emails_norm,
        phones=phones_norm,
        location=location_obj,
        links=links_obj,
        headline=headline_val,
        years_experience=years_exp_val,
        skills=skills_list,
        experience=experience_list,
        education=education_list,
        projects=projects_list,
        certifications=certifications_list,
        provenance=provenance,
        overall_confidence=0.0
    )
    
    return profile
