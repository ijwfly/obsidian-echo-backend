from typing import Optional, List
from uuid import UUID, uuid4
import datetime
from enum import Enum
from pydantic import BaseModel, Field


class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    username: str
    email: str
    password_hash: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class Vault(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    name: str
    token: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class NoteState(str, Enum):
    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    DELIVERED = "DELIVERED"

class Note(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    vault_id: UUID
    external_id: Optional[str] = None
    title: Optional[str] = None
    content: str
    state: NoteState = NoteState.PENDING
    claim_owner: Optional[str] = None
    claim_timestamp: Optional[datetime.datetime] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


