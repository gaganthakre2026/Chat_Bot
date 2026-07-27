# PDF Upload + Chunk Storage + Grounded Chat — Setup Guide

This guide walks you through the full setup: **PDF in Supabase Storage**, **text chunks + embeddings in Postgres**, and **chat answers that use only your uploaded PDF data**.

---

## Architecture (what happens when you upload)

```
User uploads PDF
       │
       ▼
POST /documents/upload  (Bearer token required)
       │
       ├── 1. Save PDF to Supabase Storage bucket `documents`
       │      Path: {user_id}/{document_id}/{filename}
       │
       ├── 2. Insert row in `documents` table (status: processing)
       │
       └── 3. Background job:
              • Extract text per page (PyMuPDF)
              • Split into chunks (LangChain splitter)
              • Generate embeddings (Gemini / OpenAI)
              • Store rows in `document_chunks` (content + vector)
              • Update document status → ready

User asks a question
       │
       ▼
POST /chat/{document_id}/message
       │
       ├── Embed the question
       ├── Vector search ONLY in chunks for that document_id + user_id
       ├── Filter chunks by similarity score
       ├── LLM answers using ONLY retrieved chunk text
       ├── Groundedness check (reject hallucinations)
       └── Save user + assistant messages in `messages` table
```

**Important:** Chat never reads the raw PDF file at question time. It only uses **chunk text stored in `document_chunks`** for that specific document.

---

## Step 1 — Create a Supabase project

1. Go to [https://supabase.com](https://supabase.com) and create a project.
2. Wait until the database is ready.
3. Open **Project Settings → API** and copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon public key** → `SUPABASE_ANON_KEY`
   - **service_role key** → `SUPABASE_SERVICE_ROLE_KEY` (backend only, never in frontend)

---

## Step 2 — Enable extensions

1. Supabase Dashboard → **Database → Extensions**
2. Enable:
   - **pgvector**
   - **pgcrypto** (usually already enabled)

---

## Step 3 — Run SQL migrations

Open **SQL Editor → New query** and run these files **in order**:

### 3a. Core tables + vector search

Run the full contents of:

`backend/migrations/001_init.sql`

This creates:

| Table | Purpose |
|-------|---------|
| `documents` | PDF metadata (filename, status, page count) |
| `document_chunks` | Chunk text + 1536-dim embedding vector |
| `chat_sessions` | Chat threads per document |
| `messages` | User/assistant chat history |
| `match_document_chunks(...)` | RPC for cosine similarity search |

### 3b. PDF storage bucket

Run the full contents of:

`backend/migrations/003_storage.sql`

This creates:

- Supabase Storage bucket **`documents`** (private, PDF only, 20 MB limit)
- `documents.storage_path` column
- Storage RLS policies (users can only access their own folder)

**Verify bucket:** Dashboard → **Storage** → you should see bucket `documents`.

---

## Step 4 — Configure Supabase Auth

1. Dashboard → **Authentication → Providers**
2. Enable **Email**
3. For local development, you can disable **Confirm email** (optional — the backend auto-confirms via service role on sign-up)

---

## Step 5 — Backend environment

```powershell
cd backend
copy .env.example .env
```

Edit `backend/.env`:

```env
SUPABASE_URL=https://YOUR-PROJECT.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_STORAGE_BUCKET=documents

LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
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

Install and start:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or on Windows:

```powershell
.\start_backend_0_0_0_0.bat
```

Health check: http://localhost:8000/health

---

## Step 6 — Frontend environment

```powershell
cd frontend
copy .env.example .env
```

Edit `frontend/.env`:

```env
VITE_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_API_BASE_URL=http://localhost:8000
```

Start:

```powershell
npm install
npm run dev
```

Open: http://localhost:5173

---

## Step 7 — Test the full flow (Swagger)

1. Open http://localhost:8000/docs

2. **Sign up / sign in**
   - `POST /auth/sign-up` or `POST /auth/sign-in`
   - Body:
     ```json
     { "email": "you@gmail.com", "password": "123456" }
     ```
   - Copy `access_token` from the response

3. **Authorize**
   - Click **Authorize** (top right)
   - Enter: `Bearer YOUR_ACCESS_TOKEN`

4. **Upload PDF**
   - `POST /documents/upload`
   - Choose a PDF file with selectable text (not a scanned image-only PDF)
   - Response status: `202 Accepted`, document `status: processing`

5. **Wait for indexing**
   - `GET /documents` until `status` becomes **`ready`**
   - If `failed`, check `error_message` and backend logs

6. **Chat (grounded on PDF only)**
   - `POST /chat/{document_id}/message`
   - Body:
     ```json
     { "question": "What does the document say about ...?" }
     ```
   - Response includes:
     - `answer` — from chunk text only
     - `retrieved_chunks` — source pages used
     - `confidence` — similarity + groundedness score
     - `grounded` — whether answer passed verification

---

## Step 8 — Test in the UI

1. Sign up / log in at http://localhost:5173
2. Click **Upload PDF**
3. Wait until document status shows **ready** (polls every 3 seconds)
4. Select the document and ask a question about its content
5. Expand sources in the chat bubble to see which page/chunk was used

---

## How chat stays strict to your PDF

| Layer | What it does |
|-------|----------------|
| **Document scope** | Vector search RPC filters by `document_id` AND `user_id` |
| **Similarity filter** | Chunks below `RAG_SIMILARITY_THRESHOLD` (default 0.55) are dropped |
| **Strict LLM prompt** | System instruction: answer ONLY from provided context |
| **Groundedness check** | Second LLM pass rejects answers not supported by chunks |
| **Not-found fallback** | Returns `"I couldn't find this in the document."` when context is insufficient |

Chat will **not** use general world knowledge. If the answer is not in the PDF chunks, it says it could not find it.

---

## Verify data in Supabase Dashboard

After upload + indexing:

| Location | What to check |
|----------|---------------|
| **Storage → documents** | PDF at `{user_id}/{document_id}/filename.pdf` |
| **Table Editor → documents** | Row with `status = ready`, `page_count > 0` |
| **Table Editor → document_chunks** | Rows with `content` text and `document_id` |
| **Table Editor → messages** | Chat messages after asking questions |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Upload returns 502 storage error | Run `003_storage.sql` or create bucket `documents` in Storage |
| Document stuck on `processing` | Check backend terminal logs; verify `GEMINI_API_KEY` is valid |
| Document `failed` — no text | PDF may be image-only; use a PDF with selectable text or OCR first |
| Chat says "not in document" | Question may not match content; try asking about text that exists in the PDF |
| Chat 409 — document not ready | Wait until `GET /documents` shows `status: ready` |
| Auth 400 invalid credentials | Use `/auth/sign-up` first; password min 6 characters |
| Embedding dimension error | Ensure `GEMINI_EMBEDDING_DIMENSIONS=1536` matches migration SQL |

---

## API reference (quick)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/sign-up` | No | Create account (auto-confirmed) |
| POST | `/auth/sign-in` | No | Get access token |
| POST | `/documents/upload` | Bearer | Upload PDF → storage + chunk indexing |
| GET | `/documents` | Bearer | List your documents |
| DELETE | `/documents/{id}` | Bearer | Delete PDF, storage file, and chunks |
| POST | `/chat/{document_id}/message` | Bearer | Ask question (PDF-grounded) |
| GET | `/chat/{session_id}/history` | Bearer | Get chat history |
