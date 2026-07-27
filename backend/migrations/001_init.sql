-- Enable UUID generation
create extension if not exists "pgcrypto";
create extension if not exists vector;

-- ============================
-- documents table
-- ============================
create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    filename text not null,
    storage_path text,
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
-- document_chunks table
-- ============================
create table if not exists document_chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    page_number integer not null,
    chunk_index integer not null,
    content text not null,
    embedding vector(1536) not null,
    created_at timestamptz not null default now(),
    unique (document_id, page_number, chunk_index)
);

create index if not exists idx_document_chunks_document_id on document_chunks(document_id);
create index if not exists idx_document_chunks_user_id on document_chunks(user_id);
create index if not exists idx_document_chunks_embedding
    on document_chunks using hnsw (embedding vector_cosine_ops);

alter table document_chunks enable row level security;

create policy "Users can view their own document chunks"
    on document_chunks for select
    using (auth.uid() = user_id);

create policy "Users can insert their own document chunks"
    on document_chunks for insert
    with check (auth.uid() = user_id);

create policy "Users can delete their own document chunks"
    on document_chunks for delete
    using (auth.uid() = user_id);

create or replace function match_document_chunks(
    target_document_id uuid,
    requesting_user_id uuid,
    query_embedding vector(1536),
    match_count integer default 6
)
returns table (
    id uuid,
    document_id uuid,
    page_number integer,
    chunk_index integer,
    content text,
    score float
)
language sql
stable
as $$
    select
        document_chunks.id,
        document_chunks.document_id,
        document_chunks.page_number,
        document_chunks.chunk_index,
        document_chunks.content,
        1 - (document_chunks.embedding <=> query_embedding) as score
    from document_chunks
    where document_chunks.document_id = target_document_id
      and document_chunks.user_id = requesting_user_id
    order by document_chunks.embedding <=> query_embedding
    limit match_count;
$$;

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
