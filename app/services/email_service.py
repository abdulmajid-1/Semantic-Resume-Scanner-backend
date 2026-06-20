"""
Email Service for generating personalized AI interview invitation emails
and sending them via SMTP (Gmail).
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

from app.models.resume import Resume
from app.models.job import Job
from app.models.user import User
from app.config import get_settings

logger = logging.getLogger(__name__)


class InterviewEmailService:
    @staticmethod
    def generate_interview_email(
        db: Session,
        resume_id: int,
        recruiter_user: User,
        date_time: str,
        job_id: int = None,
        job_title: str = None
    ):
        """Generate a personalized AI interview invitation email."""
        # 1. Fetch resume and candidate user
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            raise ValueError("Resume not found.")
            
        candidate_name = resume.parsed_name or "Candidate"
        candidate_email = resume.parsed_email or resume.user.email
        
        # 2. Determine Job Title
        actual_job_title = "Software Engineer"
        
        if job_id:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                actual_job_title = job.title
        elif job_title:
            actual_job_title = job_title
            
        # 3. Format key candidate details to personalize the email
        skills_str = ""
        if resume.candidate_skills:
            skills = [cs.skill.name for cs in resume.candidate_skills[:4]]
            skills_str = ", ".join(skills)
            
        experience_str = f"{resume.years_of_experience} years of experience" if resume.years_of_experience else "professional experience"
        
        # Build subject
        subject = f"Interview Invitation: {actual_job_title} role"
        
        # Build email body
        body = (
            f"Dear {candidate_name},\n\n"
            f"Thank you for your interest in the {actual_job_title} opportunity. We have reviewed your resume "
            f"and we are very impressed by your background.\n\n"
        )
        
        if skills_str:
            body += (
                f"In particular, we noted your strong expertise in areas such as {skills_str}. "
                f"Your {experience_str} aligns well with the requirements for this position.\n\n"
            )
        else:
            body += (
                f"We believe your {experience_str} and accomplishments make you a great match for this role.\n\n"
            )
            
        body += (
            f"We would love to invite you for a virtual technical interview to learn more about your experience "
            f"and share more details about the role.\n\n"
            f"We would like to propose the following time slot:\n"
            f"📅 Date & Time: {date_time}\n\n"
            f"Please let us know if this time works for you. If it does not, feel free to share a few alternative "
            f"slots, and we will do our best to accommodate your schedule.\n\n"
            f"We look forward to speaking with you!\n\n"
            f"Warm regards,\n\n"
            f"{recruiter_user.name}\n"
            f"Recruitment Team\n"
        )
        
        return {
            "candidate_email": candidate_email,
            "subject": subject,
            "body": body
        }

    @staticmethod
    def send_email_smtp(to_email: str, subject: str, body: str) -> bool:
        """
        Send an email using Gmail SMTP with the credentials from .env config.
        Returns True on success, raises Exception on failure.
        """
        settings = get_settings()

        if not settings.SMTP_USER or not settings.SMTP_PASSWORD or settings.SMTP_USER == "your-gmail@gmail.com":
            raise ValueError(
                "SMTP credentials not configured. Please set SMTP_USER and SMTP_PASSWORD in your .env file."
            )

        # Build the MIME message
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        # Plain text part
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Also attach an HTML version for nicer rendering in email clients
        html_body = body.replace("\n", "<br>")
        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #333; line-height: 1.6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; padding: 32px; background: #fafbfc;">
                <p>{html_body}</p>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
                <p style="font-size: 11px; color: #94a3b8;">
                    This email was sent via Semantic ATS — AI-Based Resume Intelligence & Candidate Ranking System.
                </p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        # Connect and send
        try:
            logger.info(f"Connecting to SMTP server {settings.SMTP_HOST}:{settings.SMTP_PORT}...")
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {e}")
            raise ValueError(
                "Gmail authentication failed. Make sure you are using an App Password, not your regular password. "
                "Enable 2-Step Verification and generate an App Password at https://myaccount.google.com/apppasswords"
            )
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            raise
