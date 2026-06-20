"""
Skill Extraction Service.
Uses spaCy NLP and pre-defined skill mappings to extract categorized skills from text.
"""

import re
import spacy
from typing import List, Dict, Tuple, Set
from sqlalchemy.orm import Session
import logging

from app.models.skill import Skill, CandidateSkill, SkillCategory
from app.skill_extractor.skill_database import SKILLS_DICTIONARY

logger = logging.getLogger(__name__)


class SkillExtractorService:
    def __init__(self):
        self.nlp = None

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

    def extract_skills_from_text(self, text: str) -> List[Tuple[str, SkillCategory]]:
        """
        Scans a block of text and extracts known skills from the skills dictionary.
        Returns a list of tuples containing (skill_name, skill_category).
        """
        if not text:
            return []

        nlp = self._get_nlp()
        doc = nlp(text.lower())
        
        extracted = []
        text_lower = text.lower()

        # Step 1: Substring / Phrase matching for complex skills (multi-word like "spring boot", "next.js")
        # We sort skills by length descending to match longer skills first (e.g. "spring boot" before "spring")
        sorted_skills = sorted(SKILLS_DICTIONARY.keys(), key=len, reverse=True)
        
        matched_indices: Set[int] = set()

        for skill_key in sorted_skills:
            # Create regex boundary-aware pattern
            # Escape characters like . and + in keys (e.g. c++, next.js, .net)
            escaped_skill = re.escape(skill_key)
            
            # Handle special cases like c++, .net, c# where standard \b word boundaries don't work correctly
            if skill_key.endswith('+') or skill_key.endswith('#') or skill_key.startswith('.'):
                # Custom boundaries
                pattern = rf'(?:^|[\s,;:\(\)\/]){escaped_skill}(?:$|[\s,;:\(\)\/])'
            else:
                pattern = rf'\b{escaped_skill}\b'

            for match in re.finditer(pattern, text_lower):
                start, end = match.span()
                # Check if this span overlaps with any previously matched indices
                overlap = False
                for idx in range(start, end):
                    if idx in matched_indices:
                        overlap = True
                        break
                
                if not overlap:
                    # Mark indices as matched
                    for idx in range(start, end):
                        matched_indices.add(idx)
                    
                    # Store display name (match standard capitalized/normalized key name)
                    display_name = skill_key
                    # We can normalize display names for the UI, e.g., cpp -> C++, csharp -> C#
                    normalized_name = self._normalize_skill_name(display_name)
                    extracted.append((normalized_name, SKILLS_DICTIONARY[skill_key]))

        # De-duplicate skills (e.g., if a skill appears multiple times or matches synonyms)
        return list(set(extracted))

    def _normalize_skill_name(self, name: str) -> str:
        """
        Capitalizes and normalizes skill names for standard display.
        """
        mapping = {
            "python": "Python",
            "javascript": "JavaScript",
            "typescript": "TypeScript",
            "java": "Java",
            "cpp": "C++",
            "c++": "C++",
            "csharp": "C#",
            "c#": "C#",
            "c": "C",
            "ruby": "Ruby",
            "golang": "Go",
            "go": "Go",
            "rust": "Rust",
            "php": "PHP",
            "swift": "Swift",
            "kotlin": "Kotlin",
            "scala": "Scala",
            "r": "R",
            "matlab": "MATLAB",
            "html": "HTML",
            "css": "CSS",
            "sql": "SQL",
            "bash": "Bash",
            "dart": "Dart",
            "objective-c": "Objective-C",
            "perl": "Perl",
            "react": "React",
            "angular": "Angular",
            "vue": "Vue",
            "next.js": "Next.js",
            "nextjs": "Next.js",
            "express": "Express.js",
            "nest.js": "NestJS",
            "nestjs": "NestJS",
            "django": "Django",
            "flask": "Flask",
            "fastapi": "FastAPI",
            "spring": "Spring Boot",
            "spring boot": "Spring Boot",
            "laravel": "Laravel",
            "rails": "Ruby on Rails",
            "ruby on rails": "Ruby on Rails",
            "asp.net": ".NET",
            "dotnet": ".NET",
            "node": "Node.js",
            "node.js": "Node.js",
            "nodejs": "Node.js",
            "react native": "React Native",
            "flutter": "Flutter",
            "bootstrap": "Bootstrap",
            "tailwind": "Tailwind CSS",
            "tailwindcss": "Tailwind CSS",
            "postgresql": "PostgreSQL",
            "postgres": "PostgreSQL",
            "mysql": "MySQL",
            "mongodb": "MongoDB",
            "mongo": "MongoDB",
            "redis": "Redis",
            "sqlite": "SQLite",
            "oracle": "Oracle",
            "cassandra": "Cassandra",
            "elasticsearch": "Elasticsearch",
            "dynamodb": "DynamoDB",
            "firebase": "Firebase",
            "firestore": "Firebase",
            "mariadb": "MariaDB",
            "neo4j": "Neo4j",
            "pinecone": "Pinecone",
            "milvus": "Milvus",
            "chromadb": "ChromaDB",
            "aws": "AWS",
            "amazon web services": "AWS",
            "s3": "AWS S3",
            "ec2": "AWS EC2",
            "rds": "AWS RDS",
            "lambda": "AWS Lambda",
            "ecs": "AWS ECS",
            "eks": "AWS EKS",
            "azure": "Azure",
            "gcp": "GCP",
            "google cloud": "GCP",
            "google cloud platform": "GCP",
            "pandas": "Pandas",
            "numpy": "NumPy",
            "scikit-learn": "Scikit-Learn",
            "sklearn": "Scikit-Learn",
            "tensorflow": "TensorFlow",
            "pytorch": "PyTorch",
            "spacy": "spaCy",
            "nltk": "NLTK",
            "opencv": "OpenCV",
            "huggingface": "Hugging Face",
            "transformers": "Transformers",
            "keras": "Keras",
            "scipy": "SciPy",
            "matplotlib": "Matplotlib",
            "seaborn": "Seaborn",
            "redux": "Redux",
            "graphql": "GraphQL",
            "langchain": "LangChain",
            "llamaindex": "LlamaIndex",
            "docker": "Docker",
            "kubernetes": "Kubernetes",
            "git": "Git",
            "github": "GitHub",
            "gitlab": "GitLab",
            "jenkins": "Jenkins",
            "ansible": "Ansible",
            "terraform": "Terraform",
            "postman": "Postman",
            "webpack": "Webpack",
            "vite": "Vite",
            "npm": "npm",
            "yarn": "Yarn",
            "pnpm": "pnpm",
            "poetry": "Poetry",
            "nginx": "Nginx",
            "apache": "Apache",
            "github actions": "GitHub Actions",
            "ci/cd": "CI/CD",
            "cicd": "CI/CD",
            "rest": "REST APIs",
            "restful": "REST APIs",
            "api": "REST APIs",
            "apis": "REST APIs",
            "microservices": "Microservices",
            "grpc": "gRPC",
            "jwt": "JWT",
            "oauth": "OAuth",
            "tdd": "TDD",
            "bdd": "BDD",
            "agile": "Agile",
            "scrum": "Scrum",
            "kanban": "Kanban",
        }
        return mapping.get(name.lower(), name.capitalize())

    def save_candidate_skills(self, db: Session, resume_id: int, extracted_skills: List[Tuple[str, SkillCategory]]):
        """
        Saves candidate skills to database, ensuring the skills are defined in the master skill table first.
        """
        for skill_name, category in extracted_skills:
            # 1. Look up or create master skill
            master_skill = db.query(Skill).filter(Skill.name == skill_name).first()
            if not master_skill:
                master_skill = Skill(name=skill_name, category=category)
                db.add(master_skill)
                db.commit()
                db.refresh(master_skill)

            # 2. Add relation if not exists
            exists = db.query(CandidateSkill).filter(
                CandidateSkill.resume_id == resume_id,
                CandidateSkill.skill_id == master_skill.id
            ).first()
            
            if not exists:
                cand_skill = CandidateSkill(
                    resume_id=resume_id,
                    skill_id=master_skill.id,
                    proficiency_level="Intermediate"  # default
                )
                db.add(cand_skill)
        
        db.commit()
