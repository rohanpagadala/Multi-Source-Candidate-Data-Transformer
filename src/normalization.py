import re
from typing import Optional, Dict

MONTH_MAP = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12"
}

COUNTRY_MAP = {
    "india": "IN", "in": "IN", "ind": "IN",
    "united states": "US", "us": "US", "usa": "US", "united states of america": "US",
    "united kingdom": "GB", "uk": "GB", "gbr": "GB",
    "canada": "CA", "ca": "CA",
    "germany": "DE", "de": "DE",
    "singapore": "SG", "sg": "SG"
}

SKILL_SYNONYMS = {
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "dl": "Deep Learning",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "pydantic": "Pydantic",
    "python": "Python",
    "git": "Git",
    "sql": "SQL",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes"
}

def normalize_email(email: str) -> Optional[str]:
    email = email.strip().lower()
    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return email
    return None

def normalize_phone(phone: str) -> str:
    # Remove non-digit characters, keep leading plus if present
    phone_clean = phone.strip()
    has_plus = phone_clean.startswith('+')
    digits = re.sub(r'\D', '', phone_clean)
    
    if not digits:
        return ""
    
    if len(digits) == 10:
        # Default 10 digit numbers to +91 (India) or +1 (US). Let's prefix +91 as requested in spec: 9876543210 -> +919876543210
        return f"+91{digits}"
    
    if has_plus:
        return f"+{digits}"
    
    # If starts with 91 and is 12 digits
    if len(digits) == 12 and digits.startswith('91'):
        return f"+{digits}"
    
    # If starts with 1 and is 11 digits
    if len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"

    return f"+{digits}"

def normalize_date(date_str: str) -> Optional[str]:
    if not date_str:
        return None
    date_str = date_str.strip().lower()
    if date_str in ["present", "current", "now", "ongoing"]:
        return "Present"
        
    # Check YYYY-MM pattern
    m_yyyy_mm = re.match(r'^(\d{4})[-/](\d{1,2})$', date_str)
    if m_yyyy_mm:
        year, month = m_yyyy_mm.groups()
        return f"{year}-{int(month):02d}"

    # Check MM-YYYY or MM/YYYY pattern
    m_mm_yyyy = re.match(r'^(\d{1,2})[-/](\d{4})$', date_str)
    if m_mm_yyyy:
        month, year = m_mm_yyyy.groups()
        if 1 <= int(month) <= 12:
            return f"{year}-{int(month):02d}"
        
    # Check YYYY pattern
    m_yyyy = re.match(r'^(\d{4})$', date_str)
    if m_yyyy:
        return f"{m_yyyy.group(1)}-01"  # Default to January of that year

    # Check "MMM YYYY" or "MMMM YYYY" pattern
    m_text = re.search(r'([a-zA-Z]+)\s*(\d{4})', date_str)
    if m_text:
        month_word, year = m_text.groups()
        month_num = MONTH_MAP.get(month_word[:3])
        if month_num:
            return f"{year}-{month_num}"

    # Try any 4 digit year in the string
    m_year_fallback = re.search(r'\b(20\d{2}|19\d{2})\b', date_str)
    if m_year_fallback:
        return f"{m_year_fallback.group(1)}-01"

    return None

def normalize_country(country_str: str) -> str:
    if not country_str:
        return ""
    country_clean = country_str.strip().lower()
    return COUNTRY_MAP.get(country_clean, country_str.upper())

def normalize_skill(skill_name: str) -> str:
    skill_clean = skill_name.strip().lower()
    if skill_clean in SKILL_SYNONYMS:
        return SKILL_SYNONYMS[skill_clean]
        
    special_cases = {
        "fastapi": "FastAPI",
        "next.js": "Next.js",
        "langchain": "LangChain",
        "faiss": "FAISS",
        "mongodb": "MongoDB",
        "mysql": "MySQL",
        "scikit-learn": "Scikit-learn",
        "numpy": "NumPy",
        "pytorch": "PyTorch",
        "tensorflow": "TensorFlow"
    }
    return special_cases.get(skill_clean, skill_name.strip().title())

def parse_location(location_str: str) -> Dict[str, str]:
    # e.g., "Hyderabad, TG, India" or "San Francisco, CA, USA"
    parts = [p.strip() for p in location_str.split(',')]
    city, region, country = "", "", ""
    if len(parts) == 3:
        city, region, country = parts[0], parts[1], parts[2]
    elif len(parts) == 2:
        city, country = parts[0], parts[1]
    elif len(parts) == 1:
        country = parts[0]
        
    return {
        "city": city,
        "region": region,
        "country": normalize_country(country)
    }
