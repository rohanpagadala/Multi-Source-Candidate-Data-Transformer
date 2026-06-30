import json
import os
from typing import List
from src.extractors.base import BaseExtractor
from src.models import RawFact

class ATSExtractor(BaseExtractor):
    def can_extract(self, file_path: str, content: bytes) -> bool:
        name = os.path.basename(file_path).lower()
        return 'ats' in name and file_path.lower().endswith('.json')

    def extract(self, file_path: str, content: bytes) -> List[RawFact]:
        facts = []
        source = os.path.basename(file_path)
        try:
            data = json.loads(content.decode('utf-8'))
        except Exception as e:
            print(f"Error parsing ATS JSON {source}: {e}")
            return facts

        # Extract name
        details = data.get("candidate_details", {})
        first_name = details.get("first_name", "")
        last_name = details.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            facts.append(RawFact(field="full_name", value=full_name, source=source, method="ats_json_field", confidence=1.0))

        # Extract email & phone
        contact = details.get("contact", {})
        email = contact.get("mail")
        if email:
            facts.append(RawFact(field="email", value=email, source=source, method="ats_json_field", confidence=1.0))
        phone = contact.get("telephone")
        if phone:
            facts.append(RawFact(field="phone", value=phone, source=source, method="ats_json_field", confidence=1.0))

        # Extract jobs
        for job in data.get("jobs", []):
            comp = job.get("company_name")
            title = job.get("role_title")
            if comp and title:
                facts.append(RawFact(
                    field="experience_item",
                    value={
                        "company": comp,
                        "title": title,
                        "start": job.get("from_date"),
                        "end": job.get("to_date"),
                        "summary": job.get("responsibilities", "")
                    },
                    source=source,
                    method="ats_json_field",
                    confidence=1.0
                ))

        # Extract education
        for edu in data.get("academic_history", []):
            school = edu.get("school")
            if school:
                facts.append(RawFact(
                    field="education_item",
                    value={
                        "institution": school,
                        "degree": edu.get("degree_earned"),
                        "field": edu.get("major"),
                        "end_year": edu.get("grad_year")
                    },
                    source=source,
                    method="ats_json_field",
                    confidence=1.0
                ))

        return facts
