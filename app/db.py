import logging
import asyncpg
from typing import Optional, List
from uuid import UUID
from app.models import User, Vault, Note

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.pool.Pool] = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(dsn=self.dsn)
        logger.info("Connected to database.")

    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed.")

    async def create_user(self, user: User) -> User:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (id, username, email, password_hash, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, username, email, password_hash, created_at, updated_at
                """,
                str(user.id), user.username, user.email, user.password_hash,
                user.created_at, user.updated_at
            )
            return User(**row)

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", str(user_id))
            if row:
                return User(**row)
            return None

    async def create_vault(self, vault: Vault) -> Vault:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO vaults (id, user_id, name, token, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, user_id, name, token, created_at, updated_at
                """,
                str(vault.id), str(vault.user_id), vault.name, vault.token,
                vault.created_at, vault.updated_at
            )
            return Vault(**row)

    async def get_vault_by_token(self, token: str) -> Optional[Vault]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM vaults WHERE token = $1", token)
            if row:
                return Vault(**row)
            return None

    async def create_note(self, note: Note) -> Note:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO notes (id, vault_id, external_id, title, content, state, claim_owner, claim_timestamp, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id, vault_id, external_id, title, content, state, claim_owner, claim_timestamp, created_at, updated_at
                """,
                str(note.id), str(note.vault_id), note.external_id, note.title,
                note.content, note.state.value, note.claim_owner, note.claim_timestamp,
                note.created_at, note.updated_at
            )
            return Note(**row)

    async def claim_note(self, note_id: UUID, client_id: str) -> Optional[Note]:
        """
        Try too claim a note. If the note is in 'PENDING' state, change it to 'CLAIMED',
        write client_id and timestamp.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    UPDATE notes
                    SET state = 'CLAIMED',
                        claim_owner = $2,
                        claim_timestamp = NOW(),
                        updated_at = NOW()
                    WHERE id = $1 AND state = 'PENDING'
                    RETURNING id, vault_id, external_id, title, content, state, claim_owner, claim_timestamp, created_at, updated_at
                    """,
                    str(note_id), client_id
                )
                if row:
                    return Note(**row)
            return None

    async def download_note(self, note_id: UUID) -> Optional[Note]:
        """
        Get note for download.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM notes WHERE id = $1", str(note_id))
            if row:
                return Note(**row)
            return None

    async def confirm_note(self, note_id: UUID) -> Optional[Note]:
        """
        Confirm note delivery. If the note is in 'CLAIMED' state, change it to 'DELIVERED'.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE notes
                SET state = 'DELIVERED', updated_at = NOW()
                WHERE id = $1 AND state = 'CLAIMED'
                RETURNING id, vault_id, external_id, title, content, state, claim_owner, claim_timestamp, created_at, updated_at
                """,
                str(note_id)
            )
            if row:
                return Note(**row)
            return None

    async def get_vaults_by_user(self, user_id: UUID) -> List[Vault]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM vaults WHERE user_id = $1", str(user_id))
            return [Vault(**row) for row in rows]

    async def get_user_vault(self, vault_id: UUID, user_id: UUID) -> Optional[Vault]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM vaults WHERE id = $1 AND user_id = $2", str(vault_id), str(user_id))
            if row:
                return Vault(**row)
            return None

    async def update_vault(self, vault_id: UUID, name: str, user_id: UUID) -> Optional[Vault]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE vaults SET name = $1, updated_at = NOW() WHERE id = $2 AND user_id = $3 RETURNING *",
                name, str(vault_id), str(user_id)
            )
            if row:
                return Vault(**row)
            return None

    async def delete_vault(self, vault_id: UUID, user_id: UUID) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM vaults WHERE id = $1 AND user_id = $2", str(vault_id), str(user_id))
            return result.split()[-1] != "0"

    async def get_notes_by_vault(self, vault_id: UUID, limit: int = 10, offset: int = 0) -> List[Note]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM notes WHERE vault_id = $1 ORDER BY created_at ASC LIMIT $2 OFFSET $3",
                str(vault_id), limit, offset
            )
            return [Note(**dict(row)) for row in rows]

    async def get_notes_by_state(self, vault_id: UUID, state: str, limit: int = 10, offset: int = 0) -> List[Note]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM notes WHERE vault_id = $1 AND state = $2 ORDER BY created_at ASC LIMIT $3 OFFSET $4",
                str(vault_id), state, limit, offset
            )
            return [Note(**dict(row)) for row in rows]
