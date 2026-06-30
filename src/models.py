from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict

class RawFact(BaseModel):
    field: str
    value: Any
    source: str
    method: str
    confidence: float = 1.0

class Location(BaseModel):
    city: str = ""
    region: str = ""
    country: str = ""

class Links(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    other: List[str] = []

class Skill(BaseModel):
    name: str
    confidence: float = 1.0
    sources: List[str] = []

class Experience(BaseModel):
    company: str
    title: str
    start: Optional[str] = None  # YYYY-MM
    end: Optional[str] = None    # YYYY-MM or "Present"
    summary: Optional[str] = ""

class Education(BaseModel):
    institution: str
    degree: Optional[str] = None
    field: Optional[str] = None
    end_year: Optional[str] = None  # YYYY

class Project(BaseModel):
    name: str
    description: Optional[str] = ""
    technologies: List[str] = []

class Certification(BaseModel):
    name: str
    issuing_organization: Optional[str] = None
    year: Optional[str] = None

class ProvenanceRecord(BaseModel):
    field: str
    source: str
    method: str
    confidence: float
    value: Any

class CanonicalProfile(BaseModel):
    candidate_id: str
    full_name: str
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    location: Location = Field(default_factory=Location)
    links: Links = Field(default_factory=Links)
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills: List[Skill] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    certifications: List[Certification] = Field(default_factory=list)
    provenance: List[ProvenanceRecord] = Field(default_factory=list)
    overall_confidence: float = 0.0
