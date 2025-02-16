import os

POSTGRES_HOST = 'postgres'
POSTGRES_PORT = 5432
POSTGRES_USER = 'postgres'
POSTGRES_PASSWORD = 'password'
POSTGRES_DATABASE = 'obsidianecho'

def get_postgres_dsn():
    return f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}'

JWT_EXPIRE_MINUTES = 24 * 60
JWT_ALGORITHM = "HS256"
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("Environment variable JWT_SECRET is not set")
