# Master Prompt — Use this to build the project (e.g., in Claude Code)

Copy everything below into your AI coding assistant. Attach/paste the PRD and TRD alongside it if your tool supports file attachments — it will use them as the source of truth.

---

I want you to build a full-stack **PDF-grounded RAG chatbot**. Follow the attached PRD and TRD exactly as the source of truth for requirements and architecture. Build this incrementally, one phase at a time, and confirm each phase works before moving to the next.

**Stack (do not substitute):**
- Frontend: React (Vite) + TailwindCSS
- Backend: FastAPI (Python 3.11+)
- RAG orchestration: LangGraph
- Vector database: Pinecone
- Relational DB + Auth: Supabase (Postgres + Supabase Auth, with Row-Level Security)
- LLM + Embeddings: OpenAI (or Anthropic, if I specify) via API — keep the provider swappable behind a thin client wrapper

**Database schema (Supabase / Postgres) — use this exact SQL, do not regenerate it differently:**

```sql
-- Enable UUID generation
create extension if not exists "pgcrypto";

-- ============================
-- documents table
-- ============================
create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    filename text not null,
    pinecone_namespace text not null,
    page_count integer default 0,
    status text not null default 'processing' check (status in ('processing', 'ready', 'failed')),
    error_message text,
    created_at timestamptz not null default now()
);

create index if not exists idx_documents_user_id on documents(user_id);

alter table documents enable row level security;

create policy "Users can view their own documents"
    on documents for select
    using (auth.uid() = user_id);

create policy "Users can insert their own documents"
    on documents for insert
    with check (auth.uid() = user_id);

create policy "Users can update their own documents"
    on documents for update
    using (auth.uid() = user_id);

create policy "Users can delete their own documents"
    on documents for delete
    using (auth.uid() = user_id);

-- ============================
-- chat_sessions table
-- ============================
create table if not exists chat_sessions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    document_id uuid not null references documents(id) on delete cascade,
    title text default 'New Chat',
    created_at timestamptz not null default now()
);

create index if not exists idx_chat_sessions_user_id on chat_sessions(user_id);
create index if not exists idx_chat_sessions_document_id on chat_sessions(document_id);

alter table chat_sessions enable row level security;

create policy "Users can view their own chat sessions"
    on chat_sessions for select
    using (auth.uid() = user_id);

create policy "Users can insert their own chat sessions"
    on chat_sessions for insert
    with check (auth.uid() = user_id);

create policy "Users can update their own chat sessions"
    on chat_sessions for update
    using (auth.uid() = user_id);

create policy "Users can delete their own chat sessions"
    on chat_sessions for delete
    using (auth.uid() = user_id);

-- ============================
-- messages table
-- ============================
create table if not exists messages (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references chat_sessions(id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    retrieved_chunks jsonb default '[]'::jsonb,
    confidence float check (confidence >= 0 and confidence <= 1),
    grounded boolean default true,
    created_at timestamptz not null default now()
);

create index if not exists idx_messages_session_id on messages(session_id);

alter table messages enable row level security;

-- messages are accessed via their parent chat_session's user_id
create policy "Users can view messages in their own sessions"
    on messages for select
    using (
        exists (
            select 1 from chat_sessions
            where chat_sessions.id = messages.session_id
            and chat_sessions.user_id = auth.uid()
        )
    );

create policy "Users can insert messages in their own sessions"
    on messages for insert
    with check (
        exists (
            select 1 from chat_sessions
            where chat_sessions.id = messages.session_id
            and chat_sessions.user_id = auth.uid()
        )
    );

create policy "Users can delete messages in their own sessions"
    on messages for delete
    using (
        exists (
            select 1 from chat_sessions
            where chat_sessions.id = messages.session_id
            and chat_sessions.user_id = auth.uid()
        )
    );
```

Run this in the Supabase SQL editor before starting backend development. Use it as-is for the migration file in Phase 2 below — do not redesign the schema.

**Build in this order:**

1. **Project scaffolding**
   - Set up `backend/` (FastAPI + Poetry/pip requirements.txt) and `frontend/` (Vite React) as separate folders in one repo.
   - Add `.env.example` files listing all required environment variables (Pinecone API key, Supabase URL/keys, LLM API key) — never hardcode secrets.

2. **Supabase schema**
   - Save the SQL provided above as a migration file (e.g. `backend/migrations/001_init.sql`) and add setup instructions for running it in the Supabase SQL editor. Do not regenerate the schema — use it exactly as given.

3. **PDF ingestion pipeline**
   - Implement PDF text extraction (PyMuPDF), preserving page numbers.
   - Implement chunking (recursive splitter, ~500–800 tokens, ~10–15% overlap).
   - Implement embedding generation and upsert into a Pinecone namespace per document.
   - Wire this into a FastAPI endpoint `POST /documents/upload` that runs ingestion as a background task and updates document status in Supabase.

4. **LangGraph RAG pipeline**
   - Build a `StateGraph` with nodes: `retrieve_node → grade_relevance_node → generate_node → groundedness_check_node → format_response_node`, matching the state shape and logic in the TRD.
   - Enforce strict groundedness: if no relevant chunk is found above the similarity threshold, return "I couldn't find this in the document" instead of generating freely.
   - Compute and return a confidence score using the formula described in the TRD.

5. **FastAPI endpoints**
   - Implement all endpoints listed in the TRD (`/documents/upload`, `/documents`, `/documents/{id}` DELETE, `/chat/{document_id}/message`, `/chat/{session_id}/history`, `/health`).
   - Validate Supabase JWTs on every protected route.
   - Ensure chat responses return exactly: final answer, retrieved context chunks (text + page + score), and confidence score — as defined in the TRD's example response.

6. **React frontend**
   - Auth screens (Supabase Auth: sign up / log in).
   - PDF upload UI with progress/status polling.
   - Chat interface: message bubbles, an expandable "Sources" panel per bot message showing retrieved chunks/pages/scores, and a confidence badge (High/Medium/Low or %).
   - Document list/switcher for multiple uploaded PDFs.
   - Wire everything to the FastAPI backend via a typed API client.

7. **Polish & deployment readiness**
   - Add error handling, loading states, and empty states throughout the UI.
   - Add basic logging on the backend (request id, latency, token usage).
   - Provide a README with setup instructions for local dev and deployment (frontend on Vercel/Netlify, backend on Render/Railway/Fly.io, Pinecone index setup, Supabase project setup).

**Constraints throughout:**
- Never let the frontend call Pinecone or the LLM directly — always route through FastAPI.
- Never expose the Supabase service role key or any API keys to the frontend.
- Keep the LLM/embedding provider behind an interface so it can be swapped later.
- After each phase, show me the files you created/changed and a brief summary before proceeding to the next phase.

Start with Phase 1 now.
