from pydantic import BaseModel
from typing import Optional, List

class CheckResponse(BaseModel):
    phone_number: str
    enrolled: bool

class HealthResponse(BaseModel):
    status: str
    message: str