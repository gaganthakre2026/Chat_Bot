-- PDF file storage in Supabase Storage + documents.storage_path column

alter table documents
    add column if not exists storage_path text;

create index if not exists idx_documents_storage_path on documents(storage_path);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'documents',
    'documents',
    false,
    20971520,
    array['application/pdf']::text[]
)
on conflict (id) do update
set
    public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "Users can read their own PDF files" on storage.objects;
drop policy if exists "Users can upload their own PDF files" on storage.objects;
drop policy if exists "Users can delete their own PDF files" on storage.objects;

create policy "Users can read their own PDF files"
    on storage.objects for select
    using (
        bucket_id = 'documents'
        and auth.uid()::text = (storage.foldername(name))[1]
    );

create policy "Users can upload their own PDF files"
    on storage.objects for insert
    with check (
        bucket_id = 'documents'
        and auth.uid()::text = (storage.foldername(name))[1]
    );

create policy "Users can delete their own PDF files"
    on storage.objects for delete
    using (
        bucket_id = 'documents'
        and auth.uid()::text = (storage.foldername(name))[1]
    );
