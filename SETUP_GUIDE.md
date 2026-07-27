# PDF Upload + Chunk Storage + Grounded Chat — Setup Guide

This guide walks you through the full pipeline:

1. PDF uploaded to the backend  
2. Original PDF stored in **Supabase Storage**  
3. Text split into **chunks** with embeddings in **`document_chunks`**  
4. Chat answers **only from that indexed PDF data**

---

## Architecture

```
User uploads PDF
       │
       ▼
POST /documents/upload  (Bearer token required)
       │
       ├── Save PDF → Supabase Storage bucket "documents"
       │              path: {user_id}/{document_id}/{filename}.pdf
       │
       ├── Insert row → documents table (status: processing)
       │
       └── Background job:
              ├── Extract text per page (PyMuPDF)
              ├── Split into chunks (LangChain splitter)
              ├── Generate embeddings (Gemini / OpenAI)
              └── Insert rows → document_chunks table
                     status → ready

User asks question
       │
       ▼
POST /chat/{document_id}/message
       │
       ├── Embed the question
       ├── Vector search ONLY in this document's chunks (pgvector RPC)
       ├── Filter by similarity threshold
       ├── LLM answer using ONLY retrieved chunks
       └── Groundedness check → reject hallucinated answers
```

---

## Step 1 — Supabase project

1. Go to [https://supabase.com](https://supabase.com) and open your project.
2. **Database → Extensions** → enable:
   - `pgvector`
   - `pgcrypto` (usually already on)

---

## Step 2 — Run SQL migrations

Open **Supabase → SQL Editor → New query**.

### A. Tables + vector search (required)

Copy and run the full contents of:

```
backend/migrations/001_init.sql
```

This creates:

| Object | Purpose |
|--------|---------|
| `documents` | PDF metadata + status |
| `document_chunks` | Text chunks + `vector(1536)` embeddings |
| `chat_sessions` | Chat threads per document |
| `messages` | User/assistant messages |
| `match_document_chunks(...)` | Cosine similarity search scoped to one PDF |

### B. PDF storage bucket (required)

Copy and run:

```
backend/migrations/003_storage.sql
```

This creates:

- Storage bucket `documents` (private, PDF only, 20 MB limit)
- `documents.storage_path` column
- Storage RLS policies (users access only their own files)

> **Note:** The backend can also create the bucket automatically on first upload, but running this SQL ensures policies and the `storage_path` column exist.

---

## Step 3 — Enable auth

1. **Authentication → Providers → Email** → enable Email provider.
2. For local development you do **not** need email confirmation — the backend auto-confirms users via the service role on sign-up.

---

## Step 4 — Collect Supabase keys

**Project Settings → API**

| Key | Where it goes |
|-----|----------------|
| Project URL | `SUPABASE_URL` / `VITE_SUPABASE_URL` |
| anon / publishable key | `SUPABASE_ANON_KEY` / frontend env |
| service_role key | `SUPABASE_SERVICE_ROLE_KEY` (**backend only, never frontend**) |

---

## Step 5 — Backend environment

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env`:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_STORAGE_BUCKET=documents

LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-key
GEMINI_CHAT_MODEL=gemini-3.6-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
GEMINI_EMBEDDING_DIMENSIONS=1536

RAG_TOP_K=6
RAG_SIMILARITY_THRESHOLD=0.55
CHUNK_SIZE_CHARS=3000
CHUNK_OVERLAP_CHARS=450
UPLOAD_MAX_MB=20
CORS_ORIGINS=http://localhost:5173
```

Start the API:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or run `start_backend_0_0_0_0.bat`.

Health check: http://localhost:8000/health

---

## Step 6 — Frontend environment

```powershell
cd frontend
npm install
copy .env.example .env
```

Edit `frontend/.env`:

```env
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your-publishable-or-anon-key
VITE_API_BASE_URL=http://localhost:8000
```

Start the UI:

```powershell
npm run dev
```

Open http://localhost:5173

---

## Step 7 — Create an account

### Option A — Web UI

1. Open http://localhost:5173  
2. Click **Sign up**  
3. Enter email + password (min 6 characters)  
4. You are signed in immediately (no email confirmation needed)

### Option B — Swagger / API

1. Open http://localhost:8000/docs  
2. `POST /auth/sign-up` with:

```json
{
  "email": "you@gmail.com",
  "password": "yourpassword"
}
```

3. Copy `access_token` from the response  
4. Click **Authorize** → enter: `Bearer YOUR_ACCESS_TOKEN`

---

## Step 8 — Upload a PDF

### Web UI

1. Click **Upload PDF**  
2. Select a text-based PDF (scanned images without OCR may fail)  
3. Wait until status shows **ready** (polls every 3 seconds)

### API

```http
POST /documents/upload
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: multipart/form-data

file: (your PDF)
```

Response (`202 Accepted`):

```json
{
  "document": {
    "id": "...",
    "filename": "report.pdf",
    "storage_path": "user-id/doc-id/report.pdf",
    "status": "processing",
    "page_count": 0
  }
}
```

### What happens in the database

| Location | Data |
|----------|------|
| **Supabase Storage** `documents` bucket | Original PDF file |
| **`documents` table** | Metadata, `storage_path`, status |
| **`document_chunks` table** | One row per chunk: `content`, `page_number`, `embedding` |

Check indexing:

```http
GET /documents
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Wait until `"status": "ready"`.

Verify in Supabase:

- **Storage → documents** → `{user_id}/{document_id}/yourfile.pdf`  
- **Table Editor → document_chunks** → rows for your `document_id`

---

## Step 9 — Chat (PDF-grounded answers only)

### Web UI

1. Select the **ready** document in the sidebar  
2. Type a question about the PDF content  
3. The answer includes confidence + source chunks with page numbers

### API

```http
POST /chat/{document_id}/message
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "question": "What is this document about?",
  "session_id": null
}
```

Response:

```json
{
  "answer": "...",
  "confidence": 0.82,
  "grounded": true,
  "retrieved_chunks": [
    { "text": "...", "page": 1, "score": 0.91 }
  ],
  "session_id": "..."
}
```

### How strict PDF-only answers work

1. **Scoped retrieval** — vector search runs only on chunks where `document_id` and `user_id` match the selected PDF.  
2. **Similarity filter** — chunks below `RAG_SIMILARITY_THRESHOLD` (default `0.55`) are discarded.  
3. **Strict prompt** — the LLM is instructed to use only provided context.  
4. **Groundedness check** — a second LLM pass verifies the answer is supported by the chunks; if not, the response is replaced with:  
   `"I couldn't find this in the document."`

---

## Step 10 — Verify end-to-end (quick test)

```powershell
# 1. Sign in
curl -X POST http://localhost:8000/auth/sign-in ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"you@gmail.com\",\"password\":\"yourpassword\"}"

# 2. Upload (replace TOKEN)
curl -X POST http://localhost:8000/documents/upload ^
  -H "Authorization: Bearer TOKEN" ^
  -F "file=@C:\path\to\your.pdf"

# 3. List documents until status=ready
curl http://localhost:8000/documents -H "Authorization: Bearer TOKEN"

# 4. Ask a question (replace DOCUMENT_ID)
curl -X POST http://localhost:8000/chat/DOCUMENT_ID/message ^
  -H "Authorization: Bearer TOKEN" ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"Summarize page 1\"}"
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Sign-up "invalid email" / rate limit | Use backend `/auth/sign-up` (auto-confirms). Wait a few minutes if Supabase email rate limit was hit. |
| Upload 502 storage error | Run `003_storage.sql` or ensure bucket `documents` exists in Storage. |
| Document status `failed` | PDF may have no selectable text. Use a text PDF or OCR first. Check `error_message` in `documents` table. |
| Chat says "couldn't find in document" | Question may not match indexed text. Lower `RAG_SIMILARITY_THRESHOLD` slightly (e.g. `0.45`). |
| Chat 409 "no indexed chunks" | Re-upload; wait for `ready` status. |
| Embeddings dimension error | `GEMINI_EMBEDDING_DIMENSIONS` must match SQL (`1536`). |

---

## API reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| POST | `/auth/sign-up` | No | Create account + get tokens |
| POST | `/auth/sign-in` | No | Sign in |
| POST | `/auth/logout` | Yes | Sign out |
| POST | `/documents/upload` | Yes | Upload PDF → storage + chunk indexing |
| GET | `/documents` | Yes | List your documents |
| DELETE | `/documents/{id}` | Yes | Delete PDF, storage file, and chunks |
| POST | `/chat/{document_id}/message` | Yes | Ask question (PDF-grounded) |
| GET | `/chat/{session_id}/history` | Yes | Get chat history |

All authenticated routes require:

```http
Authorization: Bearer <access_token>
```
