from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DrawConfig(BaseModel):
    sources: List[str] = Field(default_factory=lambda: ["news", "weather", "os", "time", "solar", "meteo_sat"])  # available: news, weather, os, time, solar, meteo_sat
    bits: int = 4096
    numbers: int = 6
    max_number: int = 49


class DrawBitsResponse(BaseModel):
    job_id: str
    bits: str
    length: int

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


# NIST SP 800-22
class NistStartResponse(BaseModel):
    job_id: str


class NistTestCase(BaseModel):
    name: str
    passed: bool
    p_value: float
    note: Optional[str] = None


class NistSummary(BaseModel):
    eligible: int
    total: int
    passed: int
    ratio: float


class NistReport(BaseModel):
    job_id: str
    status: str
    started_at: float
    finished_at: Optional[float] = None
    length: int
    tests: List[NistTestCase]
    summary: NistSummary


class WsInfo(BaseModel):
    url: str
    event_format: str = Field(
        description="Формат сообщения WebSocket: JSON с полями event и data"
    )
    example_message: Dict[str, Any]
    note: Optional[str] = None
