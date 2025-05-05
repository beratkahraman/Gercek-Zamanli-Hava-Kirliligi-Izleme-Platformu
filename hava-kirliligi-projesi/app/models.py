from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PollutionData(BaseModel):
    latitude: float
    longitude: float
    parameter: str
    value: float
    timestamp: Optional[datetime] = None
