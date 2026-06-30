# Intelligent Multi-Source Candidate Profile Builder

> A configurable candidate intelligence pipeline that extracts, verifies, enriches, normalizes, and consolidates candidate information from multiple sources into a unified profile.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Processing-orange)
![Pydantic](https://img.shields.io/badge/Pydantic-Validation-green)
![PDF](https://img.shields.io/badge/PDF-Resume%20Parsing-red)
![JSON](https://img.shields.io/badge/Output-JSON-success)
![CLI](https://img.shields.io/badge/Interface-CLI-lightgrey)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

# Table of Contents

- [Project Overview](#project-overview)
- [Problem Statement](#problem-statement)
- [Why This Project?](#why-this-project)
- [Objectives](#objectives)
- [Key Features](#key-features)
- [Complete System Architecture](#complete-system-architecture)
- [End-to-End Processing Pipeline](#end-to-end-processing-pipeline)
- [Data Source Priority](#data-source-priority)
- [Folder Structure](#folder-structure)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Running the Project](#running-the-project)
- [Configuration](#configuration)
- [Information Extraction](#information-extraction)
- [Verification & Enrichment Engine](#verification--enrichment-engine)
- [Data Normalization](#data-normalization)
- [Identity Resolution](#identity-resolution)
- [Merge Engine & Conflict Resolution](#merge-engine--conflict-resolution)
- [Confidence Scoring](#confidence-scoring)
- [Configurable Projection](#configurable-projection)
- [JSON Schema Validation](#json-schema-validation)
- [Example Input & Output](#example-input--output)
- [CLI Usage](#cli-usage)
- [Error Handling & Edge Cases](#error-handling--edge-cases)
- [Design Decisions](#design-decisions)
- [Future Improvements](#future-improvements)

---

# Project Overview

Modern recruitment platforms receive candidate information from multiple independent sources such as resumes, recruiter notes, ATS exports, LinkedIn profiles, and GitHub repositories. These sources often contain duplicate, incomplete, outdated, or conflicting information.

This project builds an intelligent data transformation pipeline that consolidates information from all available sources into a single validated candidate profile.

Unlike traditional resume parsers, this system performs profile verification, profile enrichment, conflict resolution, confidence scoring, and configurable output generation.

---

# Problem Statement

Recruiters frequently receive candidate information from different systems.
For example:
- **Resume**: The primary document submitted by the candidate.
- **Recruiter Notes**: Direct transcripts or human annotations containing missing skills, project details, and personal assessments.
- **ATS Export**: Semi-structured application records.
- **LinkedIn / GitHub**: Social profile states.

Each source may provide different information. Examples include:
- Missing phone numbers or emails.
- Different spellings of names.
- Additional GitHub projects and coding language skills.
- Outdated LinkedIn job roles.
- Conflicting titles and dates.

The challenge is determining:
- Which source should be trusted?
- Which information should be merged?
- Which information should be ignored?
- How can confidence be assigned?

This project solves that problem.

---

# Why This Project?

Traditional resume parsers stop after extracting text from a PDF. This project goes several steps further by:
- **Extracting structured information** across structured and unstructured data formats.
- **Validating candidate information** against professional profiles.
- **Verifying public profiles** (GitHub/LinkedIn) data.
- **Enriching missing information** from recruiter notes.
- **Resolving conflicts** via configurable source priorities.
- **Assigning confidence scores** based on source reliability and extraction methods.
- **Producing a standardized JSON profile** customized dynamically through run-time configs.

---

# Objectives

- Extract candidate information from multiple sources.
- Treat the Resume as the primary source of truth.
- Validate and enrich candidate profiles using LinkedIn and GitHub data.
- Resolve conflicting information using configurable source priorities.
- Normalize all extracted fields (phone numbers to E.164, dates to YYYY-MM, countries to ISO-3166-1 alpha-2).
- Generate a clean, structured JSON output matching a custom projection runtime schema.

---

# Key Features

- **Resume-first data processing**: Resume data forms the base, which is then enriched or updated.
- **Recruiter Notes integration**: Free-text notes are parsed for custom skills (e.g. Docker, Kubernetes) and current roles.
- **ATS / CSV integration**: Structured applicant metadata is parsed and matched.
- **LinkedIn / GitHub verification**: Professional and coding profiles enrich skills, repos, and employment timelines.
- **Conflict resolution**: System prioritizes sources dynamically (Resume/ATS > LinkedIn/GitHub > Notes).
- **Confidence scoring**: Composite confidence score is calculated per-field and overall, boosted when fields are corroborated.
- **Configurable output**: Remap, rename, filter, or omit output fields using custom JSON projection configs.
- **JSON schema validation**: Validates final outputs at runtime using dynamic Pydantic models.
- **CLI support**: Easy terminal invocation with verbose logging.

---

# Complete System Architecture

```
                    ┌────────────────────────┐
                    │ Raw Input Files (Data) │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ Detect File & Extract  │ (Resume, Notes, ATS, CSV, LinkedIn, GitHub)
                    └───────────┬────────────┘
                                │ Raw Facts (field, value, source, method)
                                ▼
                    ┌────────────────────────┐
                    │   Data Normalization   │ (E.164 Phones, YYYY-MM Dates, ISO Countries)
                    └───────────┬────────────┘
                                │ Normalized Facts
                                ▼
                    ┌────────────────────────┐
                    │   Identity Resolution  │ (Email/Phone exact, fallback to Name match)
                    └───────────┬────────────┘
                                │ Candidate Clusters
                                ▼
                    ┌────────────────────────┐
                    │ Merge & Conflict Res.  │ (Scalar source priority, Array Union/Deduplication)
                    └───────────┬────────────┘
                                │ Canonical Profile
                                ▼
                    ┌────────────────────────┐
                    │   Confidence Scorer    │ (Composite scores + corroboration boosts)
                    └───────────┬────────────┘
                                │ Scored Profile
                                ▼
                    ┌────────────────────────┐
                    │   Projection Layer     │ <--- reads config.json
                    └───────────┬────────────┘
                                │ Reshaped JSON
                                ▼
                    ┌────────────────────────┐
                    │   Schema Validation    │ (Checks dynamic model rules before writing)
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │    Output JSON File    │ (candidate.json / custom_output.json)
                    └────────────────────────┘
```

---

# End-to-End Processing Pipeline

1. **Detect**: Inspects file types and name conventions to classify file sources.
2. **Extract**: Extracts facts from files using specialized regex/prose patterns or structured readers.
3. **Normalize**: Runs normalization on phones (E.164), dates (YYYY-MM), countries (ISO-3166-1 alpha-2), and skills (synonym dictionary).
4. **Merge**: Groups facts by candidate matching key, selecting highest priority sources for scalars, and union-de-duplicating arrays.
5. **Confidence**: Computes field-level confidence (`source_reliability * extraction_certainty`) and boosts corroborating fields.
6. **Project**: Remaps paths, formats types, toggles confidence/provenance, and resolves missing values per `config.json`.
7. **Validate**: Checks projected JSON against a dynamically derived Pydantic model at runtime.

---

# Data Source Priority

| Priority | Source | Role | Source Weight |
|----------|----------|------|---------------|
| 1 | Resume | Primary source of truth | 1.0 (High) |
| 2 | ATS / CSV | Candidate metadata | 1.0 (High) |
| 3 | LinkedIn | Verification & Enrichment | 0.75 (Medium) |
| 4 | GitHub | Verification & Enrichment | 0.75 (Medium) |
| 5 | Recruiter Notes | Human-verified additional comments | 0.5 (Low) |

---

# Folder Structure

```
multi-source-candidate-transformer/
├── README.md                    # Detailed documentation and user guide
├── config.json                  # Runtime custom projection configuration
├── requirements.txt             # Python requirements
├── main.py                      # CLI Entry point
├── default_output.json          # Output when run on default canonical schema
├── custom_output.json           # Output when run on custom projection config
├── data/                        # Sample source files for testing
│   ├── resume.txt               # Text-based resume
│   ├── recruiter_notes.txt      # Recruiter text notes
│   ├── ats_candidate.json       # ATS JSON file with custom fields
│   ├── recruiter_export.csv     # Recruiter CSV export
│   ├── linkedin_profile.json    # LinkedIn profile data (mocked API)
│   └── github_profile.json      # GitHub profile data (mocked API)
├── src/
│   ├── __init__.py
│   ├── models.py                # Pydantic schemas (Fact, Canonical, Output)
│   ├── pipeline.py              # Orchestrates the stages of the pipeline
│   ├── extractors/              # Custom extractors per source type
│   │   ├── __init__.py
│   │   ├── base.py              # Base extractor interface
│   │   ├── resume.py            # Regex/keyword extractor for PDF/TXT
│   │   ├── notes.py             # Free-text recruiter note extractor
│   │   ├── ats.py               # Custom-keyed JSON ATS extractor
│   │   ├── csv_export.py        # CSV row extractor
│   │   ├── linkedin.py          # LinkedIn JSON extractor
│   │   └── github.py            # GitHub JSON extractor
│   ├── normalization.py         # Formats emails, phones, dates, country codes
│   ├── merge.py                 # Candidate grouping, source conflict resolution
│   ├── confidence.py            # Calculates field-level & overall confidence
│   ├── projection.py            # Custom JSON-path style projection re-shaper
│   └── validation.py            # Pydantic-based schema validation of output
└── tests/                       # Unit tests and regression suite
    ├── __init__.py
    ├── test_extractors.py
    ├── test_normalization.py
    ├── test_merge.py
    └── test_projection.py
```

---

# Technology Stack

- **Core**: Python 3.11+
- **Data Validation & Schemas**: Pydantic v2
- **PDF Extraction**: PyPDF v6
- **Test Framework**: Unittest

---

# Installation

1. Clone or copy the project directory to your local environment.
2. Verify Python 3.11+ is installed.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

# Running the Project

### Run all Unit Tests
To verify implementation correctness:
```bash
python3 -m unittest discover tests
```

### Run Candidate Data Transformer CLI
Run on sample data folder with **default canonical schema**:
```bash
python3 main.py --inputs data/ --output default_output.json --verbose
```

Run on sample data folder with **custom projection config**:
```bash
python3 main.py --inputs data/ --config config.json --output custom_output.json --verbose
```

---

# Configuration

The projection configuration format allows runtime reshaping of output structure:
```json
{
  "fields": [
    { "path": "full_name", "type": "string", "required": true },
    { "path": "primary_email", "from": "emails[0]", "type": "string", "required": true },
    { "path": "phone", "from": "phones[0]", "type": "string", "normalize": "E164" },
    { "path": "skills", "from": "skills[].name", "type": "string[]", "normalize": "canonical" }
  ],
  "include_confidence": true,
  "on_missing": "null"
}
```
### Configuration parameters:
- `path`: Key in output JSON dictionary.
- `from`: Path query string inside canonical profile (e.g. `emails[0]`, `skills[].name`, `location.country`). Defaults to `path` if omitted.
- `type`: Target type validation (`string`, `string[]`, `number`, `boolean`, `integer`).
- `normalize`: Projection-level normalizer override (`E164`, `canonical`).
- `required`: If `true`, fails execution if the field is missing.
- `include_confidence`: Toggles `overall_confidence` at the output root level.
- `on_missing`: Action on empty paths: `null` (sets field to null), `omit` (removes key), `error` (stops run).

---

# Information Extraction

Each source is parsed deterministically using rules, regex patterns, or structure mapping:
- **Resume txt/pdf**: Extracts full name (line 1 heuristics), emails/phones (regex), locations (line prefix matcher), social links, skills (taxonomy checks), and experience/education timelines using date parsing.
- **Recruiter Notes**: Extracts metadata using tags (e.g. `Candidate:`) and parses phrases like `knows X and Y` to extract additional skills.
- **ATS JSON**: Maps keys (e.g., `academic_history`, `responsibilities`) to canonical facts.
- **CSV Export**: Maps rows representing current employer metadata.
- **LinkedIn / GitHub**: Mocked JSON files containing profile lists and API schemas parsed directly.

---

# Verification & Enrichment Engine

Profiles are validated and enriched by checking multiple corroborating sources:
- If a skill (e.g. `Python`) appears in both the Resume and LinkedIn, they are unioned, and confidence is boosted.
- If a skill (e.g. `Docker`) appears in recruiter notes, it is appended to the candidate skills list, enriching the profile with human-verified details.

---

# Data Normalization

All facts are normalized in `src/normalization.py`:
- **Emails**: Trimmed and lowercased.
- **Phones**: Cleaned and converted to E.164 (e.g. `9876543210 -> +919876543210`).
- **Dates**: Formatted as `YYYY-MM` (e.g. `Jan 2025 -> 2025-01`).
- **Country**: Converted to ISO-3166-1 alpha-2 codes (e.g. `India -> IN`).
- **Skills**: Synonyms mapped to canonical terms (e.g. `ML -> Machine Learning`).

---

# Identity Resolution

- Candidates are identified by exact matching on normalized **email** or **phone** values.
- If no contact details exist across two source profiles, they fall back to matching on case-insensitive normalized **names**. Name-only match is flagged with a lower name-only confidence penalty.

---

# Merge Engine & Conflict Resolution

- **Scalars** (full_name, location, headline, years_experience) use a source-priority lookup table. Higher priority source values overwrite lower ones. In a tie, the value with higher extraction confidence wins.
- **Arrays** (emails, phones, skills, experience, education) are unioned.
- **Losing Values**: Instead of being discarded, losing values are preserved in the `provenance` record list at a discounted confidence score (discounted by 30%).

---

# Confidence Scoring

- **Fact Confidence**: Calculated as `Source Reliability * Extraction Certainty`.
  - Resume/ATS: `1.0`, LinkedIn/GitHub: `0.75`, Recruiter Notes: `0.5`.
  - Regex / Direct field: `1.0`, Keyword guesses / Bio prose: `0.7`.
- **Corroboration Boost**: If a fact value (e.g. `Python` skill) is confirmed by $N$ independent sources, confidence is boosted: $\text{Confidence} = \min(\text{Confidence} + 0.1 \times (N-1), 1.0)$.
- **Overall Confidence**: Average of all present field confidences.

---

# Configurable Projection

The projection layer uses runtime custom mappings to filter and shape the canonical record dynamically:
- Field queries support dotted path resolving (e.g. `location.city`).
- Supports array selection (e.g. `emails[0]`).
- Supports array mapping (e.g. `skills[].name`).

---

# JSON Schema Validation

Instead of hardcoded dictionaries, the system derives a dynamic Pydantic model at runtime based on the `fields` defined in `config.json`. The output is run through this dynamic validator, ensuring strict schema enforcement before outputting.

---

# Example Input & Output

### Example Input (`data/resume.txt` snippet)
```
Rohan Pagadala
Email: rohan.pagadala15@gmail.com
Phone: +91 98765 43210
Skills: Python, ML, Pandas
```

### Example Input (`data/recruiter_notes.txt`)
```
Candidate: Rohan Pagadala
Notes: Knows Docker and Kubernetes.
```

### Example Output (`custom_output.json`)
```json
[
  {
    "full_name": "Rohan Pagadala",
    "primary_email": "rohan.pagadala15@gmail.com",
    "phone": "+919876543210",
    "skills": [
      "Python",
      "SQL",
      "Git",
      "Machine Learning",
      "Pandas",
      "Pydantic",
      "PyTorch",
      "HTML",
      "C++",
      "multi-source-candidate-transformer",
      "Deep Learning",
      "Docker",
      "Kubernetes"
    ],
    "overall_confidence": 0.95
  }
]
```

---

# CLI Usage

1. Process a directory and output the canonical profile:
   ```bash
   python3 main.py --inputs data/ --output candidate.json --verbose
   ```
2. Process with custom projection:
   ```bash
   python3 main.py --inputs data/ --config config.json --output custom_output.json
   ```

---

# Error Handling & Edge Cases

- **Missing/garbage source file**: The extractors log errors and proceed with succeeding files. The batch run never crashes.
- **No email/phone contact information**: Pipeline falls back to normalized name-only matching to join facts across files.
- **Config requesting non-existent canonical fields**: Handled gracefully based on the config's `on_missing` settings (`null` / `omit` / `error`).
- **Duplicate skills with different cases/synonyms**: Normalized to canonical forms (e.g., `ML` and `machine learning` both normalize to `Machine Learning`) before merging.

---

# Design Decisions

1. **Layered Architecture**: The extraction layer only outputs untyped raw facts. The canonical profile is built once, and the projection layer does not mutate it. This clean separation ensures predictability and testability.
2. **Pydantic Validation**: Runtime projection schemas are dynamically compiled into Pydantic models. This leverages native Pydantic type conversions and validation speed.
3. **No External Live API Calls**: Live network requests are replaced by mock JSON states to keep execution deterministic.

---

# Future Improvements

- **Scanned Resumes OCR**: Integrate `pytesseract` to extract facts from image PDFs.
- **Semantic Synonym Mapping**: Incorporate semantic clustering or small local LLM word-embeddings to canonicalize arbitrary skill synonyms without a static map.
- **Database Backend**: Support persisting canonical profiles in a database (e.g., SQLite or PostgreSQL) with incremental merges.

---

# License
MIT License.

---

# Author
Rohan Pagadala
Eightfold Engineering Internship Assignment (Jul-Dec 2026)
