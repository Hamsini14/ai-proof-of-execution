from pydantic import BaseModel, ConfigDict # pyre-ignore[21]
from typing import Optional, List
from datetime import datetime
from enum import Enum

class EmploymentStatus(str, Enum):
    employed = "employed"
    self_employed = "self_employed"
    unemployed = "unemployed"

class LoanInput(BaseModel):
    credit_score: int
    income: float
    loan_amount: float
    existing_debt: float
    employment_status: EmploymentStatus = EmploymentStatus.employed
    loan_term: int

class DecisionResponse(BaseModel):
    decision_id: str
    model_version: str
    decision: str
    confidence: float
    input_hash: str
    execution_hash: str
    timestamp: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)

class AuditRecord(BaseModel):
    decision_id: str
    decision: str
    confidence: float
    credit_score: Optional[int] = None
    income: Optional[float] = None
    loan_amount: Optional[float] = None
    existing_debt: Optional[float] = None
    employment_status: Optional[str] = None
    loan_term: Optional[int] = None
    model_version: str
    input_hash: str
    execution_hash: str
    merkle_root: Optional[str] = None
    blockchain_tx_id: str
    status: str
    tampered: bool
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
class TamperRequest(BaseModel):
    decision: Optional[str] = None
    confidence: Optional[float] = None
    income: Optional[float] = None
    loan_amount: Optional[float] = None
    existing_debt: Optional[float] = None
    employment_status: Optional[str] = None
    loan_term: Optional[int] = None
