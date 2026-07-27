-- Run this only if you previously applied the older Pinecone-based migration.
-- It converts the project to Supabase-only vector retrieval.

create extension if not exists vector;

alter table documents
    drop column if exists pinecone_namespace;

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

drop policy if exists "Users can view their own document chunks" on document_chunks;
create policy "Users can view their own document chunks"
    on document_chunks for select
    using (auth.uid() = user_id);

drop policy if exists "Users can insert their own document chunks" on document_chunks;
create policy "Users can insert their own document chunks"
    on document_chunks for insert
    with check (auth.uid() = user_id);

drop policy if exists "Users can delete their own document chunks" on document_chunks;
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
