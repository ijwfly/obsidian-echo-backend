from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from app.security import hash_password, verify_password, create_access_token, decode_access_token

from app.models import User, Vault, Note, NoteState
from app.db import Database
from settings import get_postgres_dsn

db = Database(dsn=get_postgres_dsn())
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    created_at: datetime
    updated_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class VaultCreate(BaseModel):
    name: str

class VaultResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    token: str
    created_at: datetime
    updated_at: datetime

class NoteCreate(BaseModel):
    external_id: Optional[str] = None
    title: str
    content: str

class NoteResponse(BaseModel):
    id: UUID
    vault_id: UUID
    external_id: Optional[str] = None
    title: Optional[str] = None
    content: str
    state: str
    claim_owner: Optional[str] = None
    claim_timestamp: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    token_data = decode_access_token(token)
    user_id: str = token_data.sub
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    user = await db.get_user_by_id(UUID(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def get_current_vault(authorization: str = Header(...)) -> Vault:
    if not authorization.startswith("Bearer "):
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header")
    token = authorization[len("Bearer "):].strip()
    vault = await db.get_vault_by_token(token)
    if vault is None:
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid vault token")
    return vault

async def get_user_by_username(username: str) -> Optional[User]:
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE username = $1", username)
        if row:
             return User(**row)
    return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.close()

app = FastAPI(lifespan=lifespan)

@app.post("/api/register", response_model=UserResponse, status_code=201)
async def register(user_data: UserRegister):
    new_user = User(
         id=uuid4(),
         username=user_data.username,
         email=user_data.email,
         password_hash=hash_password(user_data.password),
         created_at=datetime.utcnow(),
         updated_at=datetime.utcnow()
    )
    created_user = await db.create_user(new_user)
    return created_user

@app.post("/api/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(str(user.id))
    return TokenResponse(access_token=access_token)

@app.get("/api/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/api/vaults", response_model=List[VaultResponse])
async def list_vaults(current_user: User = Depends(get_current_user)):
    vaults = await db.get_vaults_by_user(current_user.id)
    return vaults

@app.post("/api/vaults", response_model=VaultResponse, status_code=201)
async def create_vault_endpoint(vault_data: VaultCreate, current_user: User = Depends(get_current_user)):
    new_vault = Vault(
         id=uuid4(),
         user_id=current_user.id,
         name=vault_data.name,
         token="vault_" + str(uuid4()),
         created_at=datetime.utcnow(),
         updated_at=datetime.utcnow()
    )
    created_vault = await db.create_vault(new_vault)
    return created_vault

@app.get("/api/vaults/{vault_id}", response_model=VaultResponse)
async def get_vault(vault_id: UUID, current_user: User = Depends(get_current_user)):
    vault = await db.get_user_vault(vault_id, current_user.id)
    if not vault:
         raise HTTPException(status_code=404, detail="Vault not found")
    return vault

@app.put("/api/vaults/{vault_id}", response_model=VaultResponse)
async def update_vault(vault_id: UUID, vault_data: VaultCreate, current_user: User = Depends(get_current_user)):
    vault = await db.update_vault(vault_id, vault_data.name, current_user.id)
    if not vault:
         raise HTTPException(status_code=404, detail="Vault not found or not owned by user")
    return vault

@app.delete("/api/vaults/{vault_id}", status_code=204)
async def delete_vault(vault_id: UUID, current_user: User = Depends(get_current_user)):
    deleted = await db.delete_vault(vault_id, current_user.id)
    if not deleted:
         raise HTTPException(status_code=404, detail="Vault not found or not owned by user")
    return

@app.post("/api/notes", response_model=NoteResponse, status_code=201)
async def create_note_endpoint(note_data: NoteCreate, current_vault: Vault = Depends(get_current_vault)):
    new_note = Note(
         id=uuid4(),
         vault_id=current_vault.id,
         external_id=note_data.external_id,
         title=note_data.title,
         content=note_data.content,
         state=NoteState.PENDING,
         claim_owner=None,
         claim_timestamp=None,
         created_at=datetime.utcnow(),
         updated_at=datetime.utcnow()
    )
    created_note = await db.create_note(new_note)
    return created_note

@app.get("/api/notes", response_model=List[NoteResponse])
async def list_notes(state: Optional[str] = None, limit: int = 10, offset: int = 0, current_vault: Vault = Depends(get_current_vault)):
    if state is None:
         notes = await db.get_notes_by_vault(current_vault.id, limit, offset)
         return notes
    else:
         notes = await db.get_notes_by_state(current_vault.id, state.upper(), limit, offset)
         return notes

@app.post("/api/notes/{note_id}/claim", response_model=NoteResponse)
async def claim_note_endpoint(note_id: UUID, request: Request, current_vault: Vault = Depends(get_current_vault)):
    data = await request.json()
    client_id = data.get("client_id")
    if not client_id:
         raise HTTPException(status_code=400, detail="client_id required")
    claimed_note = await db.claim_note(note_id, client_id)
    if not claimed_note:
         raise HTTPException(status_code=409, detail="Note already claimed or not in PENDING state")
    return claimed_note

@app.get("/api/notes/{note_id}/download", response_model=NoteResponse)
async def download_note_endpoint(note_id: UUID, current_vault: Vault = Depends(get_current_vault)):
    note = await db.download_note(note_id)
    if not note or str(note.vault_id) != str(current_vault.id):
         raise HTTPException(status_code=404, detail="Note not found")
    return note

@app.post("/api/notes/{note_id}/confirm", response_model=NoteResponse)
async def confirm_note_endpoint(note_id: UUID, current_vault: Vault = Depends(get_current_vault)):
    confirmed_note = await db.confirm_note(note_id)
    if not confirmed_note:
         raise HTTPException(status_code=409, detail="Note not in CLAIMED state or not found")
    return confirmed_note
