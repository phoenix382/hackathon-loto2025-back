from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DrawConfig(BaseModel):
    sources: List[str] = Field(default_factory=lambda: ["news", "weather", "os", "time"])  # available: news, weather, os, time
    bits: int = 4096
    numbers: int = 6
    max_number: int = 49


class DrawStartResponse(BaseModel):
    job_id: str


class DrawResult(BaseModel):
    job_id: str
    status: str
    started_at: float
    finished_at: Optional[float]
    config: DrawConfig
    stages: List[Dict[str, Any]]
    draw: Optional[List[int]]
    fingerprint: Optional[str]
    tests: Optional[Dict[str, Any]]


class AuditInput(BaseModel):
    sequence_bits: Optional[str] = None  # string of 0/1
    numbers: Optional[List[int]] = None  # alternative: list of integers


class AuditResult(BaseModel):
    status: str
    length: int
    tests: Dict[str, Any]


class DemoConfig(BaseModel):
    scenario: str = Field("default", description="name of demo scenario")

