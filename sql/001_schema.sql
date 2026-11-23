-- Schema foundation. Enable RLS and define owner policies before deploying.
create extension if not exists pgcrypto;
create extension if not exists vector;
create table if not exists source_editions(id uuid primary key default gen_random_uuid(), name text not null, license text not null, provenance_url text);
create table if not exists scriptures(id uuid primary key default gen_random_uuid(),source_edition_id uuid not null references source_editions(id),shabad_id text,ang_number integer,raag text,author_attribution text,original_gurmukhi text not null,transliteration text,english_translation text,translation_source text,canonical_reference text,source_url text,embedding vector(768),embedding_model text,embedding_version text,created_at timestamptz default now(),updated_at timestamptz default now());
create table if not exists scripture_themes(id uuid primary key default gen_random_uuid(),scripture_id uuid not null references scriptures(id),theme text not null,annotation_source text,annotation_version text,review_status text);
create table if not exists user_assessments(id uuid primary key default gen_random_uuid(),user_id uuid,session_id uuid,energy_level text,emotional_state text,assessment_version text,consent_to_save boolean not null default false,created_at timestamptz default now());
create table if not exists chat_sessions(id uuid primary key default gen_random_uuid(),user_id uuid,assessment_id uuid references user_assessments(id),title text,created_at timestamptz default now(),updated_at timestamptz default now());
create table if not exists chat_messages(id uuid primary key default gen_random_uuid(),session_id uuid not null references chat_sessions(id) on delete cascade,role text not null,content text not null,created_at timestamptz default now(),model_identifier text,generation_status text);
create table if not exists message_citations(id uuid primary key default gen_random_uuid(),message_id uuid not null references chat_messages(id) on delete cascade,scripture_id uuid not null references scriptures(id),cited_span text,citation_position integer,verification_status text);
create table if not exists retrieval_events(id uuid primary key default gen_random_uuid(),session_id uuid references chat_sessions(id) on delete cascade,query_category text,filter_version text,candidate_count integer,retrieved_source_ids uuid[],retrieval_latency_ms integer,ranking_configuration_version text,created_at timestamptz default now());
create index if not exists scripture_ang_idx on scriptures(ang_number);
create index if not exists theme_lookup_idx on scripture_themes(theme,scripture_id);
create index if not exists message_session_idx on chat_messages(session_id,created_at);
create index if not exists scripture_embedding_idx on scriptures using hnsw(embedding vector_cosine_ops);
alter table user_assessments enable row level security;
alter table chat_sessions enable row level security;
alter table chat_messages enable row level security;
alter table message_citations enable row level security;
alter table retrieval_events enable row level security;
-- No client policies: private tables are denied by default. Add owner-scoped policies and auth before live use.
