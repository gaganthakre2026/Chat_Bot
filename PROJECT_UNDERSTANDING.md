# DocChat — Project Understanding Document

**One-line summary:** A full-stack PDF Q&A app where users upload PDFs, the system stores and indexes them, and a chatbot answers questions using **only** that document’s data.

---

## 1. What problem does this solve?

Users have PDF documents and want to ask questions without reading the entire file. DocChat:

1. Stores the original PDF in cloud storage  
2. Breaks the text into searchable chunks with AI embeddings  
3. Answers questions from those chunks only — not from general internet knowledge  

If the answer is not in the PDF, the bot replies: **“I don't have information about that.”**

---

## 2. Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, TailwindCSS |
| Backend | FastAPI (Python 3.11+) |
| Database | Supabase Postgres |
| Vector search | pgvector (1536-dim embeddings) |
| File storage | Supabase Storage (`documents` bucket) |
| Auth | Supabase Auth (via backend proxy) |
| LLM / embeddings | Gemini (default) or OpenAI |
| RAG orchestration | LangGraph |

---

## 3. High-level architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                        │
│  Sign in → Upload PDF → Select document → Chat + confidence     │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP (Bearer token)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                          │
│  /auth  /documents  /chat  /health                              │
└─────┬───────────────┬────────────────┬──────────────────────────┘
      │               │                │
      ▼               ▼                ▼
 Supabase Auth   Supabase Storage   Supabase Postgres
                 (original PDF)     (documents, chunks, chat)
                                           │
                                           ▼
                                    Gemini / OpenAI
                                    (embed + generate)
```

---

## 4. Repository structure

```
Chatbot_01/
├── frontend/                 # React UI
│   ├── src/
│   │   ├── App.jsx           # Auth gate + main workspace
│   │   ├── api/client.js     # All backend API calls
│   │   ├── components/       # AuthPanel, ChatWindow, UploadButton, etc.
│   │   └── lib/              # Supabase client, message helpers
│   └── vite.config.cjs       # Dev proxy → backend :8000
│
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app + CORS
│   │   ├── api/              # auth, documents, chat routes
│   │   ├── core/             # config, security, logging
│   │   ├── models/           # Pydantic schemas
│   │   ├── rag/              # LangGraph pipeline + prompts
│   │   └── services/         # Supabase, storage, LLM, ingestion
│   └── migrations/           # SQL for Supabase tables + storage
│
├── PROJECT_UNDERSTANDING.md  # This file
├── SETUP.md                  # Step-by-step setup
└── README.md                 # Quick start
```

---

## 5. Database (Supabase Postgres)

| Table | Purpose |
|-------|---------|
| `documents` | PDF metadata: filename, status, page count, optional `storage_path` |
| `document_chunks` | Text chunks + 1536-dim embedding vectors per chunk |
| `chat_sessions` | One chat thread per user per document |
| `messages` | User questions and assistant answers (with confidence + sources) |

**Document status values:** `processing` → `ready` or `failed`

**Key RPC:** `match_document_chunks(document_id, user_id, query_embedding, match_count)`  
Performs cosine similarity search scoped to one document and one user.

**Storage bucket:** `documents`  
Path pattern: `{user_id}/{document_id}/{filename}.pdf`

---

## 6. Backend API routes

All routes except `/health` require header:  
`Authorization: Bearer <supabase_access_token>`

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/health` | Health check |
| POST | `/auth/sign-up` | Create user (auto-confirmed via service role) |
| POST | `/auth/sign-in` | Login, returns tokens |
| POST | `/auth/logout` | Logout |
| POST | `/documents/upload` | Upload PDF → storage + background indexing |
| GET | `/documents` | List user’s documents |
| DELETE | `/documents/{id}` | Delete PDF, storage file, and chunks |
| POST | `/chat/{document_id}/message` | Ask a question (RAG) |
| GET | `/chat/{session_id}/history` | Load chat history |

Interactive docs: `http://localhost:8000/docs`

---

## 7. PDF upload flow (step by step)

1. User selects PDF in UI → `POST /documents/upload`
2. Backend validates PDF and saves a temp copy
3. Row inserted in `documents` with `status: processing`
4. PDF uploaded to Supabase Storage
5. **Background job** (`process_pdf_document`):
   - Extract text per page (PyMuPDF)
   - Split into chunks (~3000 chars, 450 overlap)
   - Generate embeddings (Gemini, 1536 dimensions)
   - Insert rows into `document_chunks`
   - Update document to `status: ready`
6. Frontend polls `GET /documents` until status is `ready`

---

## 8. Chat / RAG flow (step by step)

1. User sends question → `POST /chat/{document_id}/message`
2. Backend checks document is `ready` and has chunks
3. **LangGraph pipeline** runs:

```
retrieve_node          → embed question, vector search in document_chunks
       ↓
grade_relevance_node   → drop chunks below similarity threshold (0.55)
       ↓
generate_node          → LLM answer using ONLY chunk text
       ↓
groundedness_check_node → verify answer is supported by chunks
       ↓
format_response_node   → confidence score + final answer
```

4. User message + assistant reply saved in `messages`
5. Response includes: `answer`, `confidence`, `retrieved_chunks`, `session_id`

**Strict rule:** LLM system prompt forbids outside knowledge. Unsupported answers become:  
`"I don't have information about that."`

---

## 9. Frontend user flow

```
App.jsx
  │
  ├─ No session?  → AuthPanel (sign in / sign up via backend /auth)
  │
  └─ Logged in?   → Workspace
                      ├─ Header: Upload PDF, sign out
                      ├─ Sidebar: document list
                      └─ ChatWindow: messages + input + confidence badges
```

**Auth:** Frontend calls backend `/auth/*`, then stores session in Supabase client via `setSession`.

**Dev networking:** Vite proxies `/auth`, `/documents`, `/chat` to `localhost:8000` so CORS is avoided.  
Leave `VITE_API_BASE_URL` empty in local `.env`.

---

## 10. Key backend modules

| File | Role |
|------|------|
| `api/auth.py` | Sign-up (admin auto-confirm), sign-in, logout |
| `api/documents.py` | Upload, list, delete documents |
| `api/chat.py` | Send message, get history |
| `services/ingestion.py` | PDF → pages → chunks → embeddings |
| `services/supabase_storage.py` | Upload/delete PDF in bucket |
| `services/supabase_client.py` | DB operations + vector RPC |
| `services/llm_provider.py` | Gemini or OpenAI embed + generate |
| `rag/langgraph_pipeline.py` | Full RAG graph |
| `core/security.py` | Validate Bearer token via Supabase |

---

## 11. Configuration (environment variables)

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | Public anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Backend only — never expose to frontend |
| `GEMINI_API_KEY` | Yes* | *If `LLM_PROVIDER=gemini` |
| `GEMINI_EMBEDDING_DIMENSIONS` | Yes | Must match DB: `1536` |
| `SUPABASE_STORAGE_BUCKET` | Yes | Default: `documents` |
| `RAG_SIMILARITY_THRESHOLD` | No | Default: `0.55` |
| `CORS_ORIGINS` | No | Comma-separated frontend URLs |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_SUPABASE_URL` | Yes | Same as backend Supabase URL |
| `VITE_SUPABASE_ANON_KEY` | Yes | Anon key for session client |
| `VITE_API_BASE_URL` | No | Empty in dev (uses Vite proxy) |

---

## 12. Security model

- **Row Level Security (RLS)** on all Supabase tables — users only see their own data  
- **Service role key** used only on backend (bypasses RLS for indexing)  
- **Bearer token** validated on every protected API call  
- **Storage policies** — users access only their `{user_id}/` folder  
- **Groundedness check** — reduces hallucinated answers  

---

## 13. Confidence score (what it means)

Displayed on each assistant message (0–100%).

**Formula (simplified):** blend of average chunk similarity + groundedness pass/fail.

| Range | Label |
|-------|-------|
| ≥ 80% | High confidence |
| 55–79% | Medium confidence |
| < 55% | Low confidence |

Low or zero confidence often means the question did not match PDF content well.

---

## 14. Common statuses & messages

| Situation | What user sees |
|-----------|----------------|
| PDF still indexing | “Document is processing…” |
| Answer not in PDF | “I don't have information about that.” |
| Backend down | “Cannot reach the backend API…” |
| Invalid login | Error from Supabase/auth route |
| Chat before ready | HTTP 409 — wait until `ready` |

---

## 15. How to run locally (short)

**Backend:**
```powershell
cd backend
.\start_backend_0_0_0_0.bat
```

**Frontend:**
```powershell
cd frontend
npm run dev
```

**Supabase:** Run `migrations/001_init.sql` and `migrations/003_storage.sql` once.

Full details → [SETUP.md](SETUP.md)

---

## 16. Design decisions (why things are built this way)

| Decision | Reason |
|----------|--------|
| Chunks in Postgres, not raw PDF at chat time | Faster, cheaper, scoped vector search |
| 1536-dim embeddings | Supabase pgvector HNSW limit is 2000 dims |
| Backend auth proxy | Auto-confirms users; avoids email rate limits |
| LangGraph for RAG | Clear steps: retrieve → filter → generate → verify |
| Vite proxy in dev | Avoids CORS when frontend port changes (5173, 5175, etc.) |
| Background PDF processing | Upload returns immediately; indexing runs async |

---

## 17. Extending the project (safe areas)

| Want to… | Where to change |
|----------|-----------------|
| Change chunk size | `CHUNK_SIZE_CHARS` in backend `.env` |
| Change LLM model | `GEMINI_CHAT_MODEL` in backend `.env` |
| Adjust answer strictness | `RAG_SIMILARITY_THRESHOLD`, prompts in `rag/prompts.py` |
| UI styling | `frontend/src/components/` |
| Add new API route | `backend/app/api/` + register in `main.py` |

Avoid changing embedding dimensions without updating SQL migration and re-indexing all documents.

---

## 18. Quick reference — file → responsibility

| Question | Answer |
|----------|--------|
| Where is auth? | `backend/app/api/auth.py` + `frontend/src/components/AuthPanel.jsx` |
| Where is upload? | `backend/app/api/documents.py` + `frontend/src/components/UploadButton.jsx` |
| Where is chat UI? | `frontend/src/components/ChatWindow.jsx` |
| Where is RAG logic? | `backend/app/rag/langgraph_pipeline.py` |
| Where are API calls? | `frontend/src/api/client.js` |
| Where is SQL schema? | `backend/migrations/001_init.sql` |
| Where is storage setup? | `backend/migrations/003_storage.sql` |

---

*Last updated for the DocChat / PDF-Grounded RAG Chatbot codebase.*
