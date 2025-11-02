# CHAT INTERFACE PLAN

**App Goal:** Build a Django app that delivers an authenticated chat workspace with per-user limits, encrypted storage in PostgreSQL, vector persistence in ChromaDB, image/PDF ingestion via an extraction microservice, and speech-to-text support, ready for future frontend consumption.

---

## 1. Architectural Overview

- **New Django app:** `chat` inside existing `backend` project (reuse custom `authentication.User`).
- **Data stores:**
  - PostgreSQL for relational data (chats, messages, attachments, audit fields).
  - ChromaDB for semantic search over message chunks. Reuse embedding + storage pattern from `RAG_LLM.py`.
- **Supporting services:**
  - Document extraction microservice (external API) for image/PDF text extraction.
  - Speech-to-text (FastAPI WebSocket) leveraging `Speech_to_text.py` logic, exposed to frontend later.
- **Environment:** continue using conda env `auth_env`; install any new deps there (e.g., `cryptography`, `django-fernet-fields`, `langchain` extras).

---

## 2. Models & Database Schema (PostgreSQL)

Create these in `chat/models.py`:

1. **Chat**

   - `id` (auto)
   - `user` → FK to `authentication.User`
   - `name` (default `"Chat"`, editable)
   - `created_at` (auto_now_add=True). Treat the serialized UTC timestamp as the authoritative `chat_id` for metadata; enforce uniqueness per chat with `unique=True` (or derive an explicit `chat_uuid` if precision issues appear).
   - `updated_at` (auto_now=True)
   - Constraints:
     - Unique constraint on (`user`, `name`) optional (allow duplicates if user can rename arbitrarily); enforcement is not required.
     - Database/logic-level guard to limit max 3 chats per user.

2. **Message**

   - `id` (UUID primary key – deterministic metadata for vector store)
   - `chat` → FK to `Chat`
   - `sequence` (AutoField or positive integer increasing per chat for ordering)
   - `prompt_response_encrypted` (`EncryptedJSONField`) storing JSON payload: `{ "prompt": str, "response": str, "files": [attachment metadata], "extras": {...} }`
   - `raw_prompt_hash` (optional, for dedup & vector syncing)
   - `created_at`, `updated_at`
   - Signals/hooks to sync with vector store after save/delete.

3. **MessageChunkIndex** (optional tracking table)
   - `id`
   - `message` → FK to `Message`

- `chunk_id` (string from Chroma)
- `created_at`
- Useful for fast deletion when removing a message or chat.

4. **Attachment**
   - `id`
   - `message` → FK to `Message`
   - `original_name` (store filename only)
   - `file_type` (`image` | `pdf`)
   - `storage_path` / `blob_id` (nullable if only external storage references will be added later)
   - `size_bytes`
   - `page_count` (nullable; required for PDFs)
   - `created_at`
   - Validation via clean()/model constraints.

**Encryption Strategy:**

- Add dependency `django-fernet-fields` or create custom `EncryptedJSONField` using `cryptography.fernet` with a key from env var `CHAT_DATA_KEY`.
- The JSON stored should follow a consistent schema so downstream vector logic can rebuild records.

---

## 3. Application Structure

```
backend/
  chat/
    __init__.py
    apps.py
    models.py
    serializers.py
    validators.py (chat/message limits, attachment validation)
    services/
      __init__.py
      vector_store.py      # Chroma operations
      encryption.py        # wrapper if custom field not used
      document_ingestor.py # calls extraction microservice
      speech.py            # thin client for STT service (optional placeholder)
    views/
      __init__.py
      chat.py              # CRUD for chats
      message.py           # message creation/listing
    urls.py
    permissions.py (reuse DRF IsAuthenticated & check ownership)
    signals.py (vector sync on message save/delete)
    tasks.py (Celery tasks for async vector indexing / deletion)
    migrations/
```

Register the app in `INSTALLED_APPS` and add URL routes under `backend/backend/urls.py` (e.g., `path("api/chat/", include("chat.urls"))`).

---

## 4. Dependencies (install inside `auth_env`)

- `django-fernet-fields` or `django-cryptography` for encrypted JSON storage.
- `cryptography`
- `langchain-community`, `chromadb`, `huggingface-hub` (already implied by `RAG_LLM.py`).
- `requests` (already in project root), `pydantic` for request validation if needed.
- For chunking, reuse `langchain.text_splitter.RecursiveCharacterTextSplitter`.

Document installation steps (PowerShell example):

```powershell
conda activate auth_env
pip install django-fernet-fields chromadb langchain-community
```

(Extend list as needed.)

---

## 5. ChromaDB Integration

- Reuse embedding model path `ibm-granite/granite-embedding-english-r2`.
- Configure a dedicated `chat` collection (e.g., `./Long_Term_Memory` already exists; use same store with separate namespace or metadata filter).
- Metadata schema for each chunk:
  ```json
  {
    "username": user.email,
    "chat_id": chat.created_at.isoformat(),
    "message_id": str(message.id),
    "chunk_index": int,
    "source": "chat_message",
    "file_names": ["bloodwork.pdf"],
    "created_at": "2025-11-02T12:00:00Z"
  }
  ```
- Implement helper in `services/vector_store.py` with operations:
  - `upsert_message_chunks(message, combined_text, metadata)`
  - `delete_chat_vectors(username, chat_id)`
  - `delete_message_vectors(message)`
  - `search(username, chat_id, query, k=...)`
- Use text splitter with chunk size/overlap mirroring `RAG_LLM.py` (300/75) unless requirement changes.
- Handle rate limiting / retries similar to `RAG_LLM.py` if necessary.

---

## 6. Document Extraction Microservice Workflow

- Endpoint (configurable via env): `DOCUMENT_PARSER_URL` expecting `POST /extract` with multipart or JSON referencing uploaded blob.
- For each uploaded file:
  1. Validate format (images: png/jpg/jpeg/webp; PDFs only). Reject others.
  2. Check size limits (≤ 10 MB image, ≤ 25 MB PDF) before hitting microservice.
  3. For PDFs ensure page count ≤ 5 (use PyPDF2 locally or rely on microservice response metadata; if local, add dependency `pypdf`).
  4. Send file to microservice; expect JSON `{ "text": "cleaned text..." }`.
  5. Aggregate returned text and append to prompt prior to chunking.
  6. Only store filenames & metadata in Postgres.
- Place logic in `services/document_ingestor.py` for reuse.

---

## 7. Speech-to-Text Support

- Extract the model-loading/transcription flow from `Speech_to_text.py` into a dedicated FastAPI microservice (already present).
- Within Django plan, expose an endpoint to provide WebSocket URL & toggling status (e.g., `GET /api/chat/speech-token/` returning connection info). Main frontend work deferred.
- Optionally add a Django view to proxy transcript events for CLI testing later.

---

## 8. REST API Design (DRF)

All endpoints require JWT auth (use existing authentication setup).

1. **Chat List & Create**

   - `GET /api/chat/` → list chat headers: `[{ "id": 1, "name": "Chat", "chat_id": "2025-11-02T12:34:56.123456Z", "created_at": ..., "updated_at": ... }]`
   - `POST /api/chat/` with optional `name` → create new chat. Validate user has < 3 chats else 400. Default name `Chat`.

2. **Chat Rename & Delete**

   - `PATCH /api/chat/<pk>/` body `{ "name": "Pain Log" }`.
   - `DELETE /api/chat/<pk>/` → remove chat, cascade delete messages & attachments, trigger vector deletion (username + chat_id).

3. **Message List**

   - `GET /api/chat/<pk>/messages/` → returns ordered messages with decrypted payload (server decrypts, but hide encryption key). Response includes attachments metadata.

4. **Message Create**

   - `POST /api/chat/<pk>/messages/`
     - Payload fields:
       - `prompt` (string)
       - Optional `response` (string) if backend handles inference separately.
       - `images`: up to 5 files
       - `pdfs`: up to 2 files
     - Steps:
       1. Validate counts & sizes client-side and server-side.
       2. Call document ingestor for each file; aggregate extracted texts.
       3. Build combined text: prompt + response + extracted text summary.
       4. Encrypt JSON payload & save message/attachments.
       5. Call vector store upsert (sync or Celery async).
       6. Return saved message with metadata (decrypted `prompt`, `response`, attachments).

5. **Message Delete (optional)**

   - `DELETE /api/chat/messages/<message_id>/` → remove message and vectors.

6. **Vector Search Endpoint (optional for debugging)**
   - `POST /api/chat/<pk>/search/` with `query` to run semantic search in Chroma limited to that chat.

Serializer layer should handle encryption/decryption automatically for API responses.

---

## 9. Business Rules & Validation

- **Chat limit:** enforce in serializer `create()` or view before creating new Chat; query count of existing chats for user.
- **Chat ownership:** ensure user can only access their chats/messages (use custom permissions or DRF `get_queryset`).
- **Attachment validation:** centralize in `validators.py`; raise DRF `ValidationError` when constraints fail.
- **Unique chat identifier:** expose `chat_id` as `chat.created_at.isoformat()`; store same string in vector metadata. On rename, do not change `created_at`.
- **Deletion workflow:**
  - DB cascade removes messages/attachments.
  - Signal or explicit service call triggers `vector_store.delete_chat_vectors`.
  - Optionally mark deletion job and run async cleanup with Celery to avoid blocking.

---

## 10. Services & Signals

- **signals.py**

  - `post_save` on `Message` → queue Celery task (or direct call) to index message.
  - `post_delete` on `Message` → remove associated vectors.
  - `post_delete` on `Chat` → remove vectors for chat using `chat_id`.

- **Celery tasks** (optional but recommended for heavy lifting)
  - `index_message_chunks(message_id)`
  - `delete_message_chunks(message_id)`
  - `purge_chat_vectors(username, chat_id)`

If avoiding Celery initially, keep synchronous implementation with TODOs.

---

## 11. Settings & Configuration

Add to `backend/settings.py`:

- `CHAT_VECTOR_DB_PATH` (default `BASE_DIR / "Long_Term_Memory"`).
- `DOCUMENT_PARSER_URL` (microservice endpoint).
- `CHAT_DATA_KEY` (Fernet key; fail fast if missing).
- `CHAT_MAX_IMAGES = 5`, `CHAT_MAX_PDFS = 2`, `CHAT_MAX_PDF_PAGES = 5`, `CHAT_MAX_IMAGE_MB = 10`, `CHAT_MAX_PDF_MB = 25`.
- Register `chat.apps.ChatConfig`.

Update `.env.example` accordingly.

---

## 12. Implementation Steps (Suggested Order)

1. **Scaffold app** `python manage.py startapp chat` and register in settings.
2. **Define models** (`Chat`, `Message`, `Attachment`, optional `MessageChunkIndex`). Run migrations.
3. **Implement encrypted JSON field** (custom field or use third-party library). Ensure migration stores encrypted data.
4. **Build services**:
   - `vector_store.py` wrapping Chroma operations.
   - `document_ingestor.py` handling validation + microservice call.
5. **Create serializers** for chats and messages (read + write) handling encryption/decryption and attachment metadata.
6. **Write DRF views** (ViewSets or APIViews) with routers in `chat/urls.py` covering endpoints listed above.
7. **Add validation utilities** for chat limits and attachment constraints.
8. **Hook up signals / service calls** to sync PostgreSQL and Chroma.
9. **Wire Celery tasks** if asynchronous indexing desired.
10. **Expose speech-to-text config endpoint** (optional stub referencing existing FastAPI service URL).
11. **Document API usage** (update README or create `Plans/chat_interface_plan.md` – this file).
12. **Manual QA checklist** (deferred tests per instruction, but note scenarios for later automated coverage).

---

## 13. Future Considerations (beyond current scope)

- Automated tests for chat/message lifecycle, encryption integrity, and vector synchronization.
- Rate limiting on message creation / upload throughput.
- Background cleanup script to reconcile Chroma vs Postgres.
- Versioned embeddings if switching models.
- Frontend integration (React/Vue) consuming DRF endpoints, hooking into speech WebSocket and file upload UI.
- Fine-grained permissions for shared chats.

---

**Deliverable:** Implementers should follow this plan to build the Django chat interface app that satisfies the requirements without frontend work, leveraging existing services and ensuring data security and vector synchronization.
