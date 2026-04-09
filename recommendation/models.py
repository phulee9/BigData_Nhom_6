from pydantic import BaseModel
from typing import List, Optional


class CVUploadResponse(BaseModel):
    vi_tri_ung_tuyen: str
    skills: List[str]
    message: Optional[str] = None


class ManualInfoRequest(BaseModel):
    job_title: str
    skills: List[str]


class RecommendSkillsRequest(BaseModel):
    job_title: str
    skills: List[str]


class SkillItem(BaseModel):
    skill: str
    count: Optional[int] = None
    pct: Optional[float] = None


class RecommendSkillsResponse(BaseModel):
    vi_tri_ung_tuyen: str
    job_titles_gan_nhat: Optional[List[str]] = None
    top_scores: Optional[List[float]] = None
    skills_da_co: List[str]
    total_candidates: Optional[int] = None
    skills_goi_y: List[dict]


class SkillRoadmapRequest(BaseModel):
    job_title: str
    skills: List[str]


class SkillRoadmapResponse(BaseModel):
    job_title: str
    total_jobs: int
    cv_skills: List[str]
    must_have: List[dict]
    should_have: List[dict]
    nice_have: List[dict]
    error: Optional[str] = None


class CareerSwitchRequest(BaseModel):
    job_from: str
    job_to: str
    skills: List[str]


class CareerSwitchResponse(BaseModel):
    job_from: str
    job_to: str
    cv_skills: List[str]
    match_pct: float
    cv_match: List[tuple]
    common_skills: List[tuple]
    only_to_skills: List[tuple]
    need_to_learn: List[tuple]
    error: Optional[str] = None
