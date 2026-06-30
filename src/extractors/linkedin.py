import json
import os
from typing import List
from src.extractors.base import BaseExtractor
from src.models import RawFact

class LinkedInExtractor(BaseExtractor):
    def can_extract(self, file_path: str, content: bytes) -> bool:
        name = os.path.basename(file_path).lower()
        return 'linkedin' in name and file_path.lower().endswith('.json')

    def extract(self, file_path: str, content: bytes) -> List[RawFact]:
        facts = []
        source = os.path.basename(file_path)
        try:
            data = json.loads(content.decode('utf-8'))
        except Exception as e:
            print(f"Error parsing LinkedIn JSON {source}: {e}")
            return facts

        name = data.get("name")
        if name:
            facts.append(RawFact(field="full_name", value=name.strip(), source=source, method="linkedin_field", confidence=0.9))

        headline = data.get("headline")
        if headline:
            facts.append(RawFact(field="headline", value=headline.strip(), source=source, method="linkedin_field", confidence=0.9))

        url = data.get("linkedin_url")
        if url:
            facts.append(RawFact(field="linkedin_link", value=url.strip(), source=source, method="linkedin_field", confidence=1.0))

        # Experience
        for exp in data.get("experience", []):
            comp = exp.get("company")
            title = exp.get("title")
            if comp and title:
                facts.append(RawFact(
                    field="experience_item",
                    value={
                        "company": comp,
                        "title": title,
                        "start": exp.get("start_date"),
                        "end": exp.get("end_date"),
                        "summary": exp.get("description", "")
                    },
                    source=source,
                    method="linkedin_field",
                    confidence=0.9
                ))

        # Education
        for edu in data.get("education", []):
            school = edu.get("school")
            if school:
                facts.append(RawFact(
                    field="education_item",
                    value={
                        "institution": school,
                        "degree": edu.get("degree"),
                        "field": edu.get("field_of_study"),
                        "end_year": edu.get("end_year")
                    },
                    source=source,
                    method="linkedin_field",
                    confidence=0.9
                ))

        # Skills
        for skill in data.get("skills", []):
            facts.append(RawFact(field="skill", value=skill, source=source, method="linkedin_field", confidence=0.8))

        return facts
