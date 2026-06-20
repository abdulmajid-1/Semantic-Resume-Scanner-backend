"""
Seeding script to pre-populate the database with sample users, jobs, resumes, and applications.
Enables immediate out-of-the-box evaluation of candidate rankings and semantic matches.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timezone
import numpy as np

from app.database.connection import SessionLocal, engine
from app.database.base import Base
from app.models.user import User, UserRole
from app.models.job import Job
from app.models.resume import Resume
from app.models.application import Application, ApplicationStatus
from app.models.skill import Skill, CandidateSkill, JobSkill, SkillCategory
from app.auth.password import hash_password
from app.embeddings.embedding_service import EmbeddingService
from app.ranking.ranking_service import RankingService
from app.faiss_search.faiss_service import FAISSSearchService

# Resumes text samples
ALICE_RESUME = """
Alice Smith
Email: alice.smith@email.com | Phone: 123-456-7890
Location: New York, NY

Summary:
Highly motivated Python Backend Developer with 4 years of experience building scalable API services.
Expertise in FastAPI, Django, PostgreSQL, Docker, and AWS cloud deployment.

Experience:
Backend Engineer | Tech Solutions Inc. | 2022 - Present
- Designed and built high-performance backend REST APIs using FastAPI and PostgreSQL.
- Containerized services using Docker and deployed on AWS ECS.
- Improved database query performance by 30% through index optimization.

Software Engineer | WebCraft Agency | 2020 - 2022
- Maintained backend databases and developed Django web applications.
- Collaborated with front-end React developers to integrate APIs.

Education:
B.S. in Computer Science | State University | 2020

Projects:
- Microservices API: High throughput async microservices system built on FastAPI.
- Cloud Deployments: Automated Terraform scripts for multi-region AWS setup.

Certifications:
- AWS Certified Developer Associate
- Certified Kubernetes Administrator (CKA)
"""

BOB_RESUME = """
Bob Jones
Email: bob.jones@email.com | Phone: 234-567-8901
Location: San Francisco, CA

Summary:
Creative Senior Frontend Engineer with 6 years of experience specializing in React, JavaScript, and modern CSS frameworks.
Strong focus on user experience, responsive design, and state management.

Experience:
Senior Frontend Developer | DesignHub | 2021 - Present
- Led a team of developers in building a SaaS analytics dashboard using React, TypeScript, and Tailwind CSS.
- Optimized bundle sizes and code splitting, reducing initial load times by 40%.
- Integrated state management systems using Redux and Axios.

React Developer | PixelPerfect Studios | 2018 - 2021
- Built responsive user interfaces and customized components.
- Maintained legacy codebase and migrated to React Hooks.

Education:
Bachelor of Arts in Design & Technology | City College | 2018

Projects:
- Design System: Custom reusable UI component library using React and Tailwind.
- Portfolio Showcase: Headless CMS-driven personal gallery website.

Certifications:
- Certified Scrum Master (CSM)
- Frontend Development Career Path (Scrimba)
"""

CHARLIE_RESUME = """
Charlie Brown
Email: charlie.brown@email.com | Phone: 345-678-9012
Location: Austin, TX

Summary:
NLP Engineer and Data Scientist with 2 years of experience specializing in Machine Learning, NLP, and Data Analysis.
Proficient in Python, spaCy, PyTorch, pandas, numpy, and scikit-learn.

Experience:
Data Scientist | Insight AI | 2024 - Present
- Developed natural language search queries pipeline using spaCy and Sentence Transformers.
- Analyzed large datasets using pandas, numpy, and scikit-learn.
- Built prototype classifiers and topic models using PyTorch.

Data Analyst Intern | StatsGroup | 2023 - 2024
- Visualized user behavior data and generated monthly dashboard reports.

Education:
M.S. in Data Science | University of Texas | 2023
B.S. in Mathematics | University of Texas | 2021

Projects:
- Semantic Search Engine: Text similarity matching app using python, FAISS, and PyTorch.
- Customer Sentiment Analysis: Fine-tuned huggingface transformers for sentiment classification.

Certifications:
- Deep Learning Specialization (Coursera)
"""


def seed_db():
    print("Initializing Database Seeder...")
    # 1. Create tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Clear existing data to allow fresh seed
        print("Cleaning up old tables...")
        db.query(Application).delete()
        db.query(Resume).delete()
        db.query(Job).delete()
        db.query(User).delete()
        db.query(Skill).delete()
        db.commit()

        print("Seeding Users...")
        # Recruiter
        recruiter = User(
            name="Sarah Jenkins (Recruiter)",
            email="recruiter@ats.com",
            password_hash=hash_password("password123"),
            role=UserRole.RECRUITER
        )
        # Admin
        admin = User(
            name="Admin User",
            email="admin@ats.com",
            password_hash=hash_password("password123"),
            role=UserRole.ADMIN
        )
        # Candidates
        alice = User(name="Alice Smith", email="alice.smith@email.com", password_hash=hash_password("password123"), role=UserRole.CANDIDATE)
        bob = User(name="Bob Jones", email="bob.jones@email.com", password_hash=hash_password("password123"), role=UserRole.CANDIDATE)
        charlie = User(name="Charlie Brown", email="charlie.brown@email.com", password_hash=hash_password("password123"), role=UserRole.CANDIDATE)

        db.add_all([recruiter, admin, alice, bob, charlie])
        db.commit()
        db.refresh(alice)
        db.refresh(bob)
        db.refresh(charlie)
        db.refresh(recruiter)

        print("Seeding Jobs...")
        job_backend = Job(
            recruiter_id=recruiter.id,
            title="FastAPI Backend Engineer",
            description="We are looking for a backend engineer to build modern microservices. The candidate must be skilled in Python, FastAPI, PostgreSQL, Docker, and AWS cloud services. Experience with deployment and performance optimization is a plus.",
            required_skills=["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
            preferred_skills=["Git", "Kubernetes"],
            experience_required=3,
            location="Remote / New York"
        )
        
        job_frontend = Job(
            recruiter_id=recruiter.id,
            title="Senior React Frontend Developer",
            description="Join our team to build next-generation web platforms. You will design, build, and optimize responsive user interfaces. Must have deep knowledge of React, JavaScript, HTML, CSS, TypeScript, and Tailwind CSS.",
            required_skills=["React", "JavaScript", "HTML", "CSS", "TypeScript", "Tailwind CSS"],
            preferred_skills=["Vite", "Agile", "Scrum"],
            experience_required=5,
            location="San Francisco, CA"
        )

        db.add_all([job_backend, job_frontend])
        db.commit()
        db.refresh(job_backend)
        db.refresh(job_frontend)

        # Set up Job Embeddings
        embedding_service = EmbeddingService()
        embedding_service.get_or_create_job_embedding(db, job_backend.id, f"{job_backend.title}\n{job_backend.description}")
        embedding_service.get_or_create_job_embedding(db, job_frontend.id, f"{job_frontend.title}\n{job_frontend.description}")

        print("Seeding Resumes and extracting candidate skills...")
        # Alice's Resume
        resume_alice = Resume(
            user_id=alice.id,
            file_path="./uploads/alice_resume_mock.pdf",
            file_type="pdf",
            raw_text=ALICE_RESUME,
            parsed_name="Alice Smith",
            parsed_email="alice.smith@email.com",
            parsed_phone="123-456-7890",
            years_of_experience=4,
            education=[{"degree": "B.S. in Computer Science", "institution": "State University", "year": "2020"}],
            experience=[{"role": "Backend Engineer", "company": "Tech Solutions Inc.", "duration": "2022 - Present"},
                        {"role": "Software Engineer", "company": "WebCraft Agency", "duration": "2020 - 2022"}],
            projects=[{"name": "Microservices API", "description": "High throughput async microservices system built on FastAPI."},
                      {"name": "Cloud Deployments", "description": "Automated Terraform scripts for multi-region AWS setup."}],
            certifications=["AWS Certified Developer Associate", "Certified Kubernetes Administrator (CKA)"]
        )
        # Bob's Resume
        resume_bob = Resume(
            user_id=bob.id,
            file_path="./uploads/bob_resume_mock.pdf",
            file_type="pdf",
            raw_text=BOB_RESUME,
            parsed_name="Bob Jones",
            parsed_email="bob.jones@email.com",
            parsed_phone="234-567-8901",
            years_of_experience=6,
            education=[{"degree": "Bachelor of Arts in Design & Technology", "institution": "City College", "year": "2018"}],
            experience=[{"role": "Senior Frontend Developer", "company": "DesignHub", "duration": "2021 - Present"},
                        {"role": "React Developer", "company": "PixelPerfect Studios", "duration": "2018 - 2021"}],
            projects=[{"name": "Design System", "description": "Custom reusable UI component library using React and Tailwind."},
                      {"name": "Portfolio Showcase", "description": "Headless CMS-driven personal gallery website."}],
            certifications=["Certified Scrum Master (CSM)"]
        )
        # Charlie's Resume
        resume_charlie = Resume(
            user_id=charlie.id,
            file_path="./uploads/charlie_resume_mock.pdf",
            file_type="pdf",
            raw_text=CHARLIE_RESUME,
            parsed_name="Charlie Brown",
            parsed_email="charlie.brown@email.com",
            parsed_phone="345-678-9012",
            years_of_experience=2,
            education=[{"degree": "M.S. in Data Science", "institution": "University of Texas", "year": "2023"},
                       {"degree": "B.S. in Mathematics", "institution": "University of Texas", "year": "2021"}],
            experience=[{"role": "Data Scientist", "company": "Insight AI", "duration": "2024 - Present"},
                        {"role": "Data Analyst Intern", "company": "StatsGroup", "duration": "2023 - 2024"}],
            projects=[{"name": "Semantic Search Engine", "description": "Text similarity matching app using python, FAISS, and PyTorch."},
                      {"name": "Customer Sentiment Analysis", "description": "Fine-tuned huggingface transformers for sentiment classification."}],
            certifications=["Deep Learning Specialization"]
        )

        db.add_all([resume_alice, resume_bob, resume_charlie])
        db.commit()
        db.refresh(resume_alice)
        db.refresh(resume_bob)
        db.refresh(resume_charlie)

        # Extract & save skills, generate embeddings
        from app.skill_extractor.extractor_service import SkillExtractorService
        extractor = SkillExtractorService()
        
        for r_model, text in [(resume_alice, ALICE_RESUME), (resume_bob, BOB_RESUME), (resume_charlie, CHARLIE_RESUME)]:
            skills = extractor.extract_skills_from_text(text)
            extractor.save_candidate_skills(db, r_model.id, skills)
            embedding_service.get_or_create_resume_embedding(db, r_model.id, text)

        print("Seeding Applications...")
        # Candidates applying to jobs
        app1 = Application(user_id=alice.id, job_id=job_backend.id, resume_id=resume_alice.id, status=ApplicationStatus.PENDING)
        app2 = Application(user_id=bob.id, job_id=job_backend.id, resume_id=resume_bob.id, status=ApplicationStatus.PENDING)
        app3 = Application(user_id=charlie.id, job_id=job_backend.id, resume_id=resume_charlie.id, status=ApplicationStatus.PENDING)

        app4 = Application(user_id=alice.id, job_id=job_frontend.id, resume_id=resume_alice.id, status=ApplicationStatus.PENDING)
        app5 = Application(user_id=bob.id, job_id=job_frontend.id, resume_id=resume_bob.id, status=ApplicationStatus.PENDING)
        app6 = Application(user_id=charlie.id, job_id=job_frontend.id, resume_id=resume_charlie.id, status=ApplicationStatus.PENDING)

        db.add_all([app1, app2, app3, app4, app5, app6])
        db.commit()

        print("Running Ranking calculations...")
        rank_service = RankingService(db)
        rank_service.process_and_rank_candidates(job_backend.id)
        rank_service.process_and_rank_candidates(job_frontend.id)

        print("Initializing FAISS Search index...")
        faiss_service = FAISSSearchService()
        faiss_service.rebuild_index(db)

        print("Database seeded successfully!")
        print("-" * 50)
        print("Credentials for testing:")
        print("Recruiter: recruiter@ats.com / password123")
        print("Candidate Alice: alice.smith@email.com / password123")
        print("Candidate Bob: bob.jones@email.com / password123")
        print("Candidate Charlie: charlie.brown@email.com / password123")
        print("Admin: admin@ats.com / password123")
        print("-" * 50)

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_db()
