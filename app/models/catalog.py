from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class Assessment(BaseModel):
    name: str
    url: str
    description: str
    assessment_type: str
    duration: str
    skills_measured: List[str]
    job_roles: List[str]
    remote_testing_support: bool
    metadata_tags: List[str]
