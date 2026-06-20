"""
Parser service for extracting structured fields from raw resume text.
Extracts Name, Email, Phone, Education, Experience, Projects, and Certifications.
Uses NLP (spaCy) and regular expressions to parse the text.
"""

import re
import spacy
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

# Regular expressions for contact details
EMAIL_REGEX = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
PHONE_REGEX = re.compile(
    r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+?\d{10,12}'
)

# Section Headers for segmentation
SECTION_HEADERS = {
    "education": [
        "education", "academic profile", "academic background", "qualification", 
        "academic qualifications", "studies", "degree", "schooling"
    ],
    "experience": [
        "experience", "work history", "employment history", "professional experience", 
        "employment", "work experience", "career history", "jobs"
    ],
    "projects": [
        "projects", "personal projects", "academic projects", "key projects", "key-projects"
    ],
    "certifications": [
        "certifications", "licenses", "courses", "credentials", "accreditation"
    ]
}


@dataclass
class ParsedResume:
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    education: List[Dict[str, Any]] = field(default_factory=list)
    experience: List[Dict[str, Any]] = field(default_factory=list)
    projects: List[Dict[str, Any]] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    years_of_experience: int = 0
    raw_text: str = ""


class ResumeParserService:
    def __init__(self):
        # spaCy model will be loaded on demand or globally.
        # We try to use "en_core_web_sm".
        self.nlp = None
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except Exception:
            logger.warning("spaCy model 'en_core_web_sm' not found. It will be loaded/downloaded at runtime if possible.")

    def _get_nlp(self):
        if self.nlp is None:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except Exception:
                import subprocess
                import sys
                subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
                self.nlp = spacy.load("en_core_web_sm")
        return self.nlp

    def parse_resume(self, text: str) -> ParsedResume:
        """
        Parses the raw text of the resume and returns a structured ParsedResume object.
        """
        parsed = ParsedResume(raw_text=text)
        
        # 1. Extract contact details
        parsed.email = self.extract_email(text)
        parsed.phone = self.extract_phone(text)
        parsed.name = self.extract_name(text)

        # 2. Segment resume text into sections
        sections = self.segment_resume(text)

        # 3. Parse specific sections
        parsed.education = self.parse_education_section(sections.get("education", ""))
        parsed.experience = self.parse_experience_section(sections.get("experience", ""))
        parsed.projects = self.parse_projects_section(sections.get("projects", ""))
        parsed.certifications = self.parse_certifications_section(sections.get("certifications", ""))
        
        # 4. Calculate total years of experience
        parsed.years_of_experience = self.calculate_years_of_experience(parsed.experience, text)

        return parsed

    def extract_email(self, text: str) -> Optional[str]:
        matches = EMAIL_REGEX.findall(text)
        if matches:
            return matches[0].strip()
        return None

    def extract_phone(self, text: str) -> Optional[str]:
        matches = PHONE_REGEX.findall(text)
        if matches:
            return matches[0].strip()
        return None

    def extract_name(self, text: str) -> Optional[str]:
        """
        Extracts candidate's name. Usually, name is in the first 2-3 lines of a resume.
        We can use spaCy's NER (PERSON entity) on the first portion of the resume.
        """
        nlp = self._get_nlp()
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if not lines:
            return None

        # Look at the first 3 lines
        header_text = " ".join(lines[:3])
        doc = nlp(header_text)
        
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                # Ensure the name is reasonable length (e.g. 2 to 4 words)
                name_words = ent.text.split()
                if 1 < len(name_words) <= 4:
                    return ent.text.strip()

        # Fallback: Just return the first non-empty line if it doesn't look like an email/phone/link
        for line in lines[:2]:
            if "@" not in line and not any(c.isdigit() for c in line) and len(line) < 50:
                return line
        
        return "Unknown Candidate"

    def segment_resume(self, text: str) -> Dict[str, str]:
        """
        Segments the resume text into standard sections based on keywords/headers.
        """
        lines = text.split('\n')
        sections = {}
        current_section = None
        current_content = []

        for line in lines:
            line_clean = line.strip().lower()
            
            # Check if this line is a section header
            found_header = False
            for section_name, headers in SECTION_HEADERS.items():
                if any(h == line_clean or line_clean.startswith(h + " ") or line_clean.endswith(" " + h) for h in headers):
                    if current_section:
                        sections[current_section] = "\n".join(current_content)
                    current_section = section_name
                    current_content = []
                    found_header = True
                    break
            
            if not found_header:
                current_content.append(line)

        # Don't forget the last section
        if current_section:
            sections[current_section] = "\n".join(current_content)

        return sections

    def parse_education_section(self, text: str) -> List[Dict[str, Any]]:
        """
        Parses the education text to extract degree, institution, and graduation year.
        """
        if not text:
            return []

        education_list = []
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        # Degree regexes
        degree_patterns = [
            r'(B\.?\s*S\.?\s*C\.?\s*S\.?|Bachelor|B\.?\s*Tech|B\.?\s*E\.?|B\.?\s*A\.?|B\.?\s*Sc|B\.?\s*B\.?\s*A\.?|M\.?\s*S\.?|M\.?\s*Tech|M\.?\s*B\.?\s*A\.?|Ph\.?D\.?|Master|Diploma|Associate)',
            r'(Computer Science|Data Science|Software Engineering|Information Technology|Mechanical|Electrical|Physics|Mathematics|Business|Finance|Arts)'
        ]

        # Very basic sentence-by-sentence parsing
        for line in lines:
            degree_match = None
            for pattern in degree_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    degree_match = match.group(0)
                    break
            
            # Look for years (like 2018, 2022, etc.)
            year_match = re.search(r'\b(19|20)\d{2}\b', line)
            year = year_match.group(0) if year_match else None

            if degree_match or year:
                education_list.append({
                    "degree": degree_match or "Degree",
                    "institution": line, # Storing whole line as details for now
                    "year": year
                })

        return education_list

    def parse_experience_section(self, text: str) -> List[Dict[str, Any]]:
        """
        Parses work experience details.
        """
        if not text:
            return []

        experience_list = []
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        current_exp = None
        
        # Simple job title regex list
        job_titles = r'(Developer|Engineer|Manager|Analyst|Consultant|Intern|Specialist|Lead|Architect|Designer|Scientist|Programmer)'

        for line in lines:
            # Check if line contains a job title
            title_match = re.search(job_titles, line, re.IGNORECASE)
            
            # Check if line contains date range (e.g. 2020 - Present, Jan 2019 - Dec 2021)
            date_match = re.search(r'\b(19|20)\d{2}\b', line)

            if title_match:
                if current_exp:
                    experience_list.append(current_exp)
                current_exp = {
                    "role": line,
                    "company": "Company Details",
                    "duration": "Duration Info",
                    "description": ""
                }
            elif current_exp:
                current_exp["description"] += line + "\n"

        if current_exp:
            experience_list.append(current_exp)

        return experience_list

    def parse_projects_section(self, text: str) -> List[Dict[str, Any]]:
        """
        Parses projects.
        """
        if not text:
            return []

        projects_list = []
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        current_project = None
        for line in lines:
            # Treat bold-looking/short header lines as project titles
            if len(line) < 60 and (line.endswith(':') or not line.endswith('.')):
                if current_project:
                    projects_list.append(current_project)
                current_project = {
                    "name": line.strip(':'),
                    "description": ""
                }
            elif current_project:
                current_project["description"] += line + "\n"

        if current_project:
            projects_list.append(current_project)

        return projects_list

    def parse_certifications_section(self, text: str) -> List[str]:
        if not text:
            return []
        # Return non-empty lines from certifications section
        return [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) < 100]

    def calculate_years_of_experience(self, experience_list: List[Dict[str, Any]], raw_text: str) -> int:
        """
        Calculates years of experience using date ranges in experience section or regexes in raw text.
        """
        # Find all year pairs in experience or raw text
        # Example: 2018 - 2022, 2020 to Present
        total_years = 0
        date_patterns = [
            r'\b(20\d{2})\s*[-–—to]+\s*(20\d{2}|present|current)\b',
            r'\b(19\d{2})\s*[-–—to]+\s*(19\d{2}|20\d{2}|present|current)\b'
        ]
        
        found_ranges = []
        for pattern in date_patterns:
            matches = re.findall(pattern, raw_text, re.IGNORECASE)
            for start, end in matches:
                start_year = int(start)
                if end.lower() in ["present", "current"]:
                    from datetime import datetime
                    end_year = datetime.now().year
                else:
                    end_year = int(end)
                
                diff = end_year - start_year
                if 0 < diff <= 45: # Filter unreasonable values
                    found_ranges.append(diff)
        
        if found_ranges:
            total_years = sum(found_ranges)
            # If the candidate has multiple overlapping jobs, this might double count, so we cap/estimate.
            # But it serves as a robust proxy. Let's return average/sum capped at 40 years.
            return min(total_years, 40)

        # Fallback: Check if there is a phrase like "X years of experience"
        exp_phrase = re.search(r'(\d+)\+?\s*years?\s+of\s+experience', raw_text, re.IGNORECASE)
        if exp_phrase:
            return int(exp_phrase.group(1))

        return 0
