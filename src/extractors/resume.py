import re
import os
from typing import List
from io import BytesIO
from src.extractors.base import BaseExtractor
from src.models import RawFact

# A simple list of common technical skills for keyword matching
KNOWN_SKILLS = [
    "Python", "Java", "C++", "JavaScript", "HTML", "CSS", "SQL", "Git", "Docker",
    "Kubernetes", "AWS", "Machine Learning", "ML", "Deep Learning", "Pandas",
    "Numpy", "Pydantic", "PyTorch", "TensorFlow", "React", "Node.js", "Django", "Flask"
]

class ResumeExtractor(BaseExtractor):
    def can_extract(self, file_path: str, content: bytes) -> bool:
        ext = os.path.splitext(file_path.lower())[1]
        if ext in ['.txt', '.pdf', '.docx']:
            # Avoid picking up recruiter notes or other JSONs
            name = os.path.basename(file_path).lower()
            return 'notes' not in name and 'linkedin' not in name and 'github' not in name
        return False

    def extract(self, file_path: str, content: bytes) -> List[RawFact]:
        facts = []
        text = ""
        source = os.path.basename(file_path)

        ext = os.path.splitext(file_path.lower())[1]
        if ext == '.pdf':
            try:
                import pypdf
                reader = pypdf.PdfReader(BytesIO(content))
                text_parts = []
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        text_parts.append(t)
                text = "\n".join(text_parts)
            except Exception as e:
                # Log error and fallback
                print(f"Error parsing PDF {source}: {e}")
                text = ""
        elif ext == '.docx':
            try:
                import docx
                doc = docx.Document(BytesIO(content))
                text_parts = []
                for p in doc.paragraphs:
                    if p.text:
                        text_parts.append(p.text)
                text = "\n".join(text_parts)
            except Exception as e:
                print(f"Error parsing DOCX {source}: {e}")
                text = ""
        else:
            text = content.decode('utf-8', errors='ignore')

        if not text.strip():
            return facts

        # 1. Full Name: Assume first line of non-empty text, or look for Name: label
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        full_name = ""
        for line in lines:
            if line.lower().startswith("name:"):
                full_name = line.split(":", 1)[1].strip()
                break
        if not full_name and lines:
            # Let's clean standard headers like Contact/Resume
            if lines[0].lower() not in ["resume", "curriculum vitae", "cv", "candidate"]:
                full_name = lines[0]

        if full_name:
            facts.append(RawFact(field="full_name", value=full_name, source=source, method="resume_first_line", confidence=1.0))

        # 2. Email:
        email_matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        for email in email_matches:
            facts.append(RawFact(field="email", value=email, source=source, method="regex_email", confidence=1.0))

        # 3. Phone:
        # Matches formats like +91 98765 43210, 9876543210, +1-234-567-8901 etc.
        phone_matches = re.findall(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+91\s?\d{5}\s?\d{5}', text)
        # Filter matches that look like actual phone numbers (at least 7 digits)
        for phone in phone_matches:
            digits = re.sub(r'\D', '', phone)
            if len(digits) >= 10:
                facts.append(RawFact(field="phone", value=phone.strip(), source=source, method="regex_phone", confidence=1.0))

        # 4. Location: Look for Location: Hyderabad, TG, India or similar
        loc_match = re.search(r'(?:Location|Address|Address:)\s*[:\-]?\s*([^\n]+)', text, re.IGNORECASE)
        if loc_match:
            facts.append(RawFact(field="location", value=loc_match.group(1).strip(), source=source, method="regex_location", confidence=0.9))

        # 5. Links: Github and LinkedIn URLs
        links = {}
        github_match = re.search(r'(https?://(?:www\.)?github\.com/[a-zA-Z0-9\-_]+)', text, re.IGNORECASE)
        if github_match:
            links['github'] = github_match.group(1).strip()
            facts.append(RawFact(field="github_link", value=github_match.group(1).strip(), source=source, method="regex_github", confidence=1.0))

        linkedin_match = re.search(r'(https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\-_]+)', text, re.IGNORECASE)
        if linkedin_match:
            links['linkedin'] = linkedin_match.group(1).strip()
            facts.append(RawFact(field="linkedin_link", value=linkedin_match.group(1).strip(), source=source, method="regex_linkedin", confidence=1.0))

        # 6. Skills: Match known skills taxonomy
        found_skills = []
        for skill in KNOWN_SKILLS:
            # Match word boundary, case-insensitive
            if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
                found_skills.append(skill)
                facts.append(RawFact(field="skill", value=skill, source=source, method="taxonomy_keyword_match", confidence=0.8))

        # 7. Experience section parsing:
        # Look for section starting with Experience / Work Experience
        exp_sec = re.split(r'\b(?:Experience|Work Experience|Employment History)\b', text, flags=re.IGNORECASE)
        if len(exp_sec) > 1:
            # We take the text after "Experience" up to the next major section (e.g. Education, Skills)
            exp_text = re.split(r'\b(?:Education|Skills|Projects|Certifications|Objective)\b', exp_sec[1], flags=re.IGNORECASE)[0]
            # Find candidate jobs. Let's split by lines and look for patterns: "Company - Title (DateRange)"
            # E.g. Eightfold AI - Engineering Intern (Jul 2026 - Dec 2026)
            exp_lines = [l.strip() for l in exp_text.split('\n') if l.strip()]
            for l in exp_lines:
                # Ignore bullet points or text prose
                if l.startswith(("-", "—", "•", "*", "–")):
                    continue
                # Match patterns like: "Company - Title (DateRange)"
                # Separation is a dash with surrounding spaces: " - " or " – " or " — "
                m = re.search(r'^(.+?)\s+[-–—]\s+(.+?)(?:\s+[\(,]\s*([A-Za-z]+\s+\d{4}|\d{4})\s*[-–—]\s*([A-Za-z]+\s+\d{4}|\w+)\s*[\)]?)?$', l)
                if m:
                    comp = m.group(1).strip()
                    title = m.group(2).strip()
                    # Clean trailing parentheses from title
                    title = re.sub(r'[\(\)]', '', title).strip()
                    start = m.group(3).strip() if m.group(3) else None
                    end = m.group(4).strip() if m.group(4) else None
                    facts.append(RawFact(
                        field="experience_item",
                        value={"company": comp, "title": title, "start": start, "end": end, "summary": l},
                        source=source,
                        method="regex_experience_line",
                        confidence=0.8
                    ))

        # 8. Education section parsing:
        edu_sec = re.split(r'\b(?:Education|Academic History|Academic Background)\b', text, flags=re.IGNORECASE)
        if len(edu_sec) > 1:
            edu_text = re.split(r'\b(?:Experience|Skills|Projects|Certifications|Work)\b', edu_sec[1], flags=re.IGNORECASE)[0]
            edu_lines = [l.strip() for l in edu_text.split('\n') if l.strip()]
            for l in edu_lines:
                if l.startswith(("-", "—", "•", "*", "–")):
                    continue
                # E.g. IIT Hyderabad - B.Tech in Computer Science (Graduate: May 2026)
                m = re.search(r'^(.+?)\s+[-–—]\s+(.+?)(?:\(\s*Graduate:\s*([^\)]+)\))?$', l, re.IGNORECASE)
                if m:
                    inst = m.group(1).strip()
                    degree_field = m.group(2).strip()
                    
                    # Split degree and field
                    degree = degree_field
                    field = None
                    if " in " in degree_field.lower():
                        parts = re.split(r'\bin\b', degree_field, flags=re.IGNORECASE)
                        degree = parts[0].strip()
                        field = parts[1].strip()
                    elif "expected" in degree_field.lower():
                        degree = None
                    
                    end_year = None
                    # Find year in line
                    year_match = re.search(r'\b(20\d{2})\b', l)
                    if year_match:
                        end_year = year_match.group(1)

                    facts.append(RawFact(
                        field="education_item",
                        value={"institution": inst, "degree": degree, "field": field, "end_year": end_year},
                        source=source,
                        method="regex_education_line",
                        confidence=0.8
                    ))

        # 9. Projects section parsing:
        proj_sec = re.split(r'\bProjects\b', text, flags=re.IGNORECASE)
        if len(proj_sec) > 1:
            proj_text = re.split(r'\b(?:Certifications|Education|Experience|Skills|Leadership)\b', proj_sec[1], flags=re.IGNORECASE)[0]
            proj_lines = [l.strip() for l in proj_text.split('\n') if l.strip()]
            curr_proj = None
            for l in proj_lines:
                is_header = ('|' in l or '—' in l or 'github' in l.lower()) and not l.startswith(("-", "—", "•", "*", "–"))
                if is_header:
                    if curr_proj:
                        facts.append(RawFact(field="project_item", value=curr_proj, source=source, method="resume_projects", confidence=0.8))
                    
                    parts = [p.strip() for p in l.split('|')]
                    title_full = parts[0]
                    link_val = parts[1] if len(parts) > 1 else None
                    
                    title = re.sub(r'\s+[-–—]\s+.*$', '', title_full).strip()
                    curr_proj = {
                        "name": title,
                        "description": "",
                        "link": link_val,
                        "technologies": []
                    }
                elif curr_proj:
                    is_tech = any(t in l for t in ["Python", "JavaScript", "Next.js", "React", "FastAPI", "MongoDB", "Firebase"]) or '·' in l or ',' in l
                    if is_tech and not curr_proj["technologies"]:
                        tech_split = re.split(r'[,·\.]', l)
                        curr_proj["technologies"] = [t.strip() for t in tech_split if t.strip()]
                    else:
                        desc_line = re.sub(r'^[-—•\*\–]\s*', '', l).strip()
                        if curr_proj["description"]:
                            curr_proj["description"] += " " + desc_line
                        else:
                            curr_proj["description"] = desc_line
            if curr_proj:
                facts.append(RawFact(field="project_item", value=curr_proj, source=source, method="resume_projects", confidence=0.8))

        # 10. Certifications section parsing:
        cert_sec = re.split(r'\bCertifications\b', text, flags=re.IGNORECASE)
        if len(cert_sec) > 1:
            cert_text = re.split(r'\b(?:Projects|Education|Experience|Skills|Leadership)\b', cert_sec[1], flags=re.IGNORECASE)[0]
            cert_lines = [l.strip() for l in cert_text.split('\n') if l.strip()]
            for l in cert_lines:
                parts = [p.strip() for p in l.split('|')]
                if len(parts) >= 2:
                    name = parts[0]
                    org_year = parts[1]
                    year_match = re.search(r'\b(20\d{2})\b', org_year)
                    year = year_match.group(1) if year_match else None
                    org = org_year
                    if year:
                        org = re.sub(r'\b' + year + r'\b', '', org).strip()
                        org = re.sub(r'[\(\)]', '', org).strip()
                    
                    facts.append(RawFact(
                        field="certification_item",
                        value={"name": name, "issuing_organization": org, "year": year},
                        source=source,
                        method="resume_certifications",
                        confidence=0.8
                    ))

        return facts
