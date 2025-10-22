from typing import  Optional
from sqlmodel import TIMESTAMP, Field, SQLModel
from  datetime import datetime,timezone
from uuid import uuid4


class CustomBaseModel(SQLModel):
    id: int  = Field(default=None, primary_key=True)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=TIMESTAMP(timezone=True))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=TIMESTAMP(timezone=True))
    delete_at: Optional[datetime] = Field(default=None, nullable=True, sa_type=TIMESTAMP(timezone=True))
    
    
class CustomBaseUUIDModel(SQLModel):
    id: str = Field(default_factory=lambda: str(uuid4()), nullable=False, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=TIMESTAMP(timezone=True))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=TIMESTAMP(timezone=True))
    delete_at: Optional[datetime] = Field(default=None, nullable=True, sa_type=TIMESTAMP(timezone=True))
    


