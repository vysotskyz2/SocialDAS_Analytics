from datetime import datetime
from pydantic import BaseModel


class DateRangeParams(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None


class TimeSeriesPoint(BaseModel):
    date: datetime
    value: int | None
