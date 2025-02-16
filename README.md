# Obsidian Echo Backend

Obsidian Echo is a multi-user integration platform that allows external sources (e.g., AI-powered Telegram bots) to directly add notes to your Obsidian vault. The system consists of a FastAPI-based backend with a PostgreSQL database and an Obsidian plugin that periodically polls for new notes. Designed for scalability and guaranteed delivery, the system ensures that each note is downloaded exactly once—even when using Obsidian Sync across multiple devices.  

This repository contains backend for Obsidian Echo plugin.

---

## Overview

Obsidian Echo bridges the gap between external note generators and your personal knowledge base in Obsidian. The backend exposes a REST API for:

- Managing **Users** (registration, login, profile).
- Managing **Vaults** linked to users. Each vault gets a unique API token used for note integration.
- Handling **Notes** using a three-phase process:
  - **Create**: External systems create notes with an initial `PENDING` state.
  - **Claim**: An Obsidian plugin instance claims the note atomically (`CLAIMED` state) so only one of potentially many clients downloads it.
  - **Download/Confirm**: The plugin downloads the note and confirms its delivery, marking it as `DELIVERED`.

Once a note is delivered to one device, Obsidian Sync propagates it to other devices, ensuring the note is processed exactly once.

---

## Data Model

The primary entities used in the system are:

- **User**  
  Contains user credentials and profile information.

- **Vault**  
  Each vault is linked to a user and includes a unique API token. It represents the physical Obsidian vault where notes are stored.

- **Note**  
  Represents an external note with metadata such as an external ID (for idempotency), title, content, and state. The state can be:
  - `PENDING`
  - `CLAIMED`
  - `DELIVERED`

Additional (optional) entities include logs and client tracking for auditing purposes.

---

## API Endpoints

The REST API is divided into two sections based on authentication method:

### User & Vault Management (JWT Authentication)

- **POST /api/register**  
  Registers a new user.
  
- **POST /api/login**  
  Authenticates a user and returns a JWT token.

- **GET /api/me**  
  Returns the current user's profile.
  
- **Vault Endpoints** (secured via JWT):
  - **GET /api/vaults**: List vaults associated with the authenticated user.
  - **POST /api/vaults**: Create a new vault (API token is auto-generated).
  - **GET /api/vaults/{vault_id}**: Retrieve details of a specific vault.
  - **PUT /api/vaults/{vault_id}**: Update vault details.
  - **DELETE /api/vaults/{vault_id}**: Delete a vault and its associated notes.

### Note Operations (Vault API Token Authentication)

Endpoints under `/api/notes` use the vault's API token sent in the **Authorization** header.

- **POST /api/notes**  
  Create a new note (e.g., via an AI bot), which is initially marked as `PENDING`.

- **GET /api/notes**  
  Retrieve notes from a vault; supports filtering (e.g., by state such as `PENDING`) and pagination.

- **POST /api/notes/{note_id}/claim**  
  Claim a note atomically—only one client can claim a note for download by providing a `client_id`. Changes the note state from `PENDING` to `CLAIMED`.

- **GET /api/notes/{note_id}/download**  
  Download the note content. The note must be in `CLAIMED` state.

- **POST /api/notes/{note_id}/confirm**  
  Confirm the note delivery, marking it as `DELIVERED`.

---

## System Sequence Diagram

Below is the mermaid.js sequence diagram illustrating the note creation and processing flow:

```mermaid
sequenceDiagram
  participant I as External Integrator (e.g., AI Bot)
  participant B as Backend (REST API)
  participant C as Obsidian Plugin (Echo Client)
  participant S as Obsidian Sync

  I->>B: POST /api/notes\n(Create note, state=PENDING)
  B-->>I: 201 Created

  C->>B: GET /api/notes?state=PENDING
  B-->>C: [Note1, Note2, ...]
  Note over C: Check if note exists locally?

  C->>B: POST /api/notes/{id}/claim\n(client_id)
  alt Claim successful
    B-->>C: 200 OK (state=CLAIMED)
    C->>B: GET /api/notes/{id}/download
    B-->>C: Note content
    C->>Local: Save note to Vault
    C->>B: POST /api/notes/{id}/confirm
    B-->>C: 200 OK (state=DELIVERED)
    C->>S: Note synced via Obsidian Sync
  else Claim failed
    B-->>C: 409 Conflict (Already claimed)
  end
```

---

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/obsidian-echo.git
   cd obsidian-echo
   ```

2. **Install Dependencies**

   Create a virtual environment and install the required Python packages:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Database Setup**

   Set up a PostgreSQL database and update the DSN in your configuration (for example, in `app.py`):

   ```python
   DB_DSN = "postgresql://postgres:password@localhost:5432/obsidianecho"
   ```

4. **Run the Server**

   Start the FastAPI server using Uvicorn:

   ```bash
   uvicorn app:app --reload
   ```

5. **Explore the API Documentation**

   Open your browser at [http://localhost:8000/docs](http://localhost:8000/docs) to view the automatically generated OpenAPI docs.

---

## Running Integration Tests

The project includes a comprehensive integration test that exercises all API endpoints using [httpx](https://www.python-httpx.org/) in an asynchronous context. Make sure the server is running and then execute:

```bash
pytest integration_test.py
```

This test covers the full flow—from user registration and login to vault creation and complete note processing (creation, claim, download, and confirmation).

---

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests with improvements, bug fixes, or new features. Please follow the repository's coding guidelines and include tests where applicable.

---

## License

This project is licensed under the MIT License.

---

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the modern, high-performance framework.
- [asyncpg](https://github.com/MagicStack/asyncpg) for asynchronous PostgreSQL support.
- The contributions of various developers in the Obsidian community for the plugin ecosystem inspiration.

Obsidian Echo is built to help you centralize and integrate your external note workflows into your Obsidian experience seamlessly—all while ensuring data integrity and single-delivery guarantees.

Happy note-taking!
