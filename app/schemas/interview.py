from pydantic import BaseModel
from typing import Optional

class GenerateEmailRequest(BaseModel):
    resume_id: int
    job_id: Optional[int] = None
    job_title: Optional[str] = None
    date_time: str

class GenerateEmailResponse(BaseModel):
    candidate_email: str
    subject: str
    body: str

class SendEmailRequest(BaseModel):
    candidate_email: str
    subject: str
    body: str
    resume_id: int
    job_id: Optional[int] = None
