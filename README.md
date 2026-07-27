# PDF-Grounded RAG Chatbot

Full-stack PDF Q&A application built from the included PRD/TRD.

**Full setup guide:** [SETUP.md](SETUP.md) — PDF upload, Supabase Storage, chunk indexing, and grounded chat.

**Project understanding:** [PROJECT_UNDERSTANDING.md](PROJECT_UNDERSTANDING.md) — architecture, data flow, API routes, and how everything connects.

- Frontend: React + Vite + TailwindCSS
- Backend: FastAPI
- Auth, relational data, and vector search: Supabase Postgres + pgvector
- RAG orchestration: LangGraph
- LLM and embeddings: Gemini by default, with OpenAI still available behind a provider wrapper

## 1. Supabase Setup

1. Create or open your Supabase project.
2. Open the SQL editor.
3. Run [backend/migrations/001_init.sql](backend/migrations/001_init.sql).
4. Run [backend/migrations/003_storage.sql](backend/migrations/003_storage.sql) to add the PDF storage bucket and `documents.storage_path` column.
5. Enable email/password auth in Supabase Auth if it is not already enabled.

Only the frontend should receive the Supabase anon key. The service role key belongs only in the backend environment.

The backend sign-up route auto-confirms users with the service role key, so you do not need email confirmation for local development.

If you already ran the old Pinecone-based migration, run [backend/migrations/002_supabase_vectors.sql](backend/migrations/002_supabase_vectors.sql) after it.

## 2. Supabase Vector Search

The project stores PDF chunks and embeddings in the `document_chunks` table using Supabase pgvector. The default Gemini embedding size is `1536` (Supabase pgvector HNSW supports up to 2000 dimensions), so the migration creates `embedding vector(1536)` and a `match_document_chunks(...)` RPC for cosine similarity search.

## 3. Backend Local Dev

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill in `backend/.env`:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_STORAGE_BUCKET=documents
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_CHAT_MODEL=gemini-3.6-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
GEMINI_EMBEDDING_DIMENSIONS=1536
```

## PDF upload flow

1. Frontend sends the PDF to `POST /documents/upload` with the Supabase access token.
2. Backend saves the original PDF in the Supabase Storage bucket `documents` at `{user_id}/{document_id}/{filename}`.
3. Backend extracts text, splits it into chunks, generates embeddings, and stores rows in `document_chunks`.
4. The document status moves from `processing` to `ready` when indexing completes.

Run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

On Windows you can also run:

```bat
start_backend_0_0_0_0.bat
```

Health check:

```bash
curl http://localhost:8000/health
```

## 4. Frontend Local Dev

```bash
cd frontend
npm install
copy .env.example .env
```

Fill in `frontend/.env`:

```env
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your-supabase-publishable-key
VITE_API_BASE_URL=http://localhost:8000
```

Run the UI:

```bash
npm run dev
```

Open the Vite URL, usually `http://localhost:5173`.

## 5. API Surface

- `GET /health`
- `POST /auth/sign-up`
- `POST /auth/sign-in`
- `POST /auth/logout`
- `POST /documents/upload`
- `GET /documents`
- `DELETE /documents/{id}`
- `POST /chat/{document_id}/message`
- `GET /chat/{session_id}/history`

All endpoints except `/health` require a Supabase access token in:

```http
Authorization: Bearer <supabase-user-access-token>
```

## 6. Deployment Notes

Backend:

- Deploy `backend/` to Render, Railway, Fly.io, or another container host.
- Use [backend/Dockerfile](backend/Dockerfile) for container deployment.
- Set backend environment variables in the host dashboard.

Frontend:

- Deploy `frontend/` to Vercel or Netlify.
- Set `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, and `VITE_API_BASE_URL`.

Security:

- Never put `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY` in frontend variables.
- Keep Supabase RLS enabled using the provided migration.
- If a service role key was pasted into a chat or ticket, rotate it in Supabase before production use.
