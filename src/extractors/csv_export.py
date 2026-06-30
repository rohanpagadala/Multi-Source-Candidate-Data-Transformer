import csv
import io
import os
from typing import List
from src.extractors.base import BaseExtractor
from src.models import RawFact

class CSVExtractor(BaseExtractor):
    def can_extract(self, file_path: str, content: bytes) -> bool:
        return file_path.lower().endswith('.csv')

    def extract(self, file_path: str, content: bytes) -> List[RawFact]:
        facts = []
        source = os.path.basename(file_path)
        text = content.decode('utf-8', errors='ignore')
        
        # Read CSV rows
        f = io.StringIO(text)
        reader = csv.DictReader(f)
        for row in reader:
            # Map name, email, phone, current_company, title
            name = row.get("name") or row.get("Name")
            if name:
                facts.append(RawFact(field="full_name", value=name.strip(), source=source, method="csv_field", confidence=1.0))
            
            email = row.get("email") or row.get("Email")
            if email:
                facts.append(RawFact(field="email", value=email.strip(), source=source, method="csv_field", confidence=1.0))
            
            phone = row.get("phone") or row.get("Phone")
            if phone:
                facts.append(RawFact(field="phone", value=phone.strip(), source=source, method="csv_field", confidence=1.0))
            
            company = row.get("current_company") or row.get("current company") or row.get("Company")
            title = row.get("title") or row.get("Title") or row.get("role")
            if company and title:
                facts.append(RawFact(
                    field="experience_item",
                    value={
                        "company": company.strip(),
                        "title": title.strip(),
                        "start": None,
                        "end": "Present",
                        "summary": f"CSV exported current role: {title} at {company}"
                    },
                    source=source,
                    method="csv_field",
                    confidence=1.0
                ))

        return facts
