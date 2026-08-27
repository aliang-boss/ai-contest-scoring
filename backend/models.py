"""
Pydantic 数据模型
"""
from pydantic import BaseModel
from typing import Optional, Dict


class LoginRequest(BaseModel):
    username: str
    password: str


class ScoreItem(BaseModel):
    pain_point: float = 0
    workflow_embed: float = 0
    feasibility: float = 0
    transferability: float = 0
    novelty: float = 0
    workflow_design: float = 0
    experience_deposit: float = 0
    quantitative: float = 0
    quality: float = 0
    sustainability: float = 0
    end_to_end: float = 0
    documentation: float = 0
    demo_quality: float = 0
    exception_handling: float = 0


class SubmitScoreRequest(BaseModel):
    project_id: str
    judge_id: str
    items: ScoreItem
    penalty: float = 0
    timestamp: int = 0


class ComputeRequest(BaseModel):
    penalties: Dict[str, float] = {}


class JudgeCreate(BaseModel):
    id: str
    name: str
    avatar: str = ""
    username: str
    password: str


class ProjectCreate(BaseModel):
    id: str
    applicant: str
    members: str = ""
    brief: str = ""