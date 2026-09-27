-- Run once in Supabase SQL Editor, or with supabase db push.
create extension if not exists vector with schema extensions;

create table public.documents (
  id uuid primary key,
  title text not null check (length(title) between 1 and 180),
  status text not null check (status in ('extracting','embedding','ready','error','deleting')),
  page_count integer not null default 0,
  chunk_count integer not null default 0,
  error text,
  created_at timestamptz not null default now(),
  estimated_cost_usd double precision not null default 0
);

create table public.chunks (
  id uuid primary key,
  document_id uuid not null references public.documents(id) on delete cascade,
  title text not null,
  page_number integer not null check (page_number > 0),
  chunk_order integer not null check (chunk_order >= 0),
  text text not null,
  embedding extensions.vector(1536) not null,
  unique(document_id, chunk_order)
);
create index chunks_document_id on public.chunks(document_id);
-- Exact cosine search is deliberate for a 30-document demo. Add HNSW after measuring scale.
alter table public.documents enable row level security;
alter table public.chunks enable row level security;
revoke all on public.documents, public.chunks from anon, authenticated;
grant all on public.documents, public.chunks to service_role;

create function public.match_chunks(
  query_embedding extensions.vector(1536),
  match_count integer default 6,
  match_threshold double precision default 0.3
) returns table (
  id uuid, document_id uuid, title text, page_number integer,
  chunk_order integer, text text, score double precision
) language sql stable security invoker
set search_path = public, extensions
as $$
  select c.id, c.document_id, c.title, c.page_number, c.chunk_order, c.text,
         1 - (c.embedding <=> query_embedding) as score
  from public.chunks c
  join public.documents d on d.id = c.document_id
  where d.status = 'ready' and 1 - (c.embedding <=> query_embedding) >= match_threshold
  order by c.embedding <=> query_embedding
  limit least(greatest(match_count, 1), 10);
$$;
revoke all on function public.match_chunks(extensions.vector, integer, double precision) from public, anon, authenticated;
grant execute on function public.match_chunks(extensions.vector, integer, double precision) to service_role;

insert into storage.buckets(id, name, public, file_size_limit, allowed_mime_types)
values ('research-pdfs', 'research-pdfs', false, 10485760, array['application/pdf'])
on conflict (id) do update set public=false, file_size_limit=10485760, allowed_mime_types=array['application/pdf'];
-- No browser Storage policies are created. Only the backend service role accesses objects.
