from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError, Field
from settings import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES

class TokenPayload(BaseModel):
    sub: str = Field(..., description="ID пользователя")
    exp: datetime = Field(..., description="Время истечения токена")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    data = TokenPayload(sub=user_id, exp=expire)
    return jwt.encode(data.model_dump(), JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        token_data = TokenPayload(**payload)
        return token_data
    except (jwt.PyJWTError, ValidationError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
