import re
import os
from typing import List
from src.extractors.base import BaseExtractor
from src.models import RawFact
from src.extractors.resume import KNOWN_SKILLS

class NotesExtractor(BaseExtractor):
    def can_extract(self, file_path: str, content: bytes) -> bool:
        name = os.path.basename(file_path).lower()
        return 'notes' in name and file_path.lower().endswith('.txt')

    def extract(self, file_path: str, content: bytes) -> List[RawFact]:
        facts = []
        source = os.path.basename(file_path)
        text = content.decode('utf-8', errors='ignore')

        if not text.strip():
            return facts

        # 1. Candidate Name: Look for "Candidate: Rohan Pagadala" or similar
        name_match = re.search(r'(?:Candidate|Name)\s*[:\-]\s*([^\n]+)', text, re.IGNORECASE)
        if name_match:
            facts.append(RawFact(field="full_name", value=name_match.group(1).strip(), source=source, method="notes_label", confidence=0.7))

        # 2. Email:
        email_matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        for email in email_matches:
            facts.append(RawFact(field="email", value=email, source=source, method="notes_email", confidence=0.7))

        # 3. Phone:
        phone_matches = re.findall(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+91\s?\d{5}\s?\d{5}', text)
        for phone in phone_matches:
            digits = re.sub(r'\D', '', phone)
            if len(digits) >= 10:
                facts.append(RawFact(field="phone", value=phone.strip(), source=source, method="notes_phone", confidence=0.7))

        # 4. Skills extraction: Search for known skills or phrases like "knows Docker"
        for skill in KNOWN_SKILLS:
            if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
                facts.append(RawFact(field="skill", value=skill, source=source, method="notes_keyword_match", confidence=0.6))

        # Extra skill extraction from "knows X and Y"
        extra_skills = re.findall(r'knows\s+([a-zA-Z\+]+(?:\s+and\s+[a-zA-Z\+]+)?)', text, re.IGNORECASE)
        for chunk in extra_skills:
            # Split by "and"
            for skill_name in re.split(r'\band\b', chunk, flags=re.IGNORECASE):
                skill_name = skill_name.strip()
                if skill_name:
                    # Let's see if it's already matches a known skill or is a new one like Kubernetes or Docker
                    # Capitalize nicely
                    norm_skill = skill_name.title()
                    # Add as skill fact
                    facts.append(RawFact(field="skill", value=norm_skill, source=source, method="notes_phrase_extraction", confidence=0.6))

        # 5. Experience / Current role: "Current company is Eightfold (intern)"
        company_match = re.search(r'Current company is\s*([a-zA-Z0-9\s\-,]+)(?:\(([^)]+)\))?', text, re.IGNORECASE)
        if company_match:
            comp = company_match.group(1).strip()
            title = company_match.group(2).strip() if company_match.group(2) else "Employee"
            facts.append(RawFact(
                field="experience_item",
                value={"company": comp, "title": title, "start": None, "end": "Present", "summary": f"Current company mentioned: {comp}"},
                source=source,
                method="notes_current_company",
                confidence=0.7
            ))

        return facts
