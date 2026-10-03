-- Durable usage logging for the public MCP server (Railway keeps only ~7 days of logs).
create table if not exists public.mcp_tool_calls (
  id             bigint generated always as identity primary key,
  created_at     timestamptz not null default now(),
  tool           text not null,
  arguments      jsonb,
  ok             boolean not null default true,
  error          text,
  duration_ms    integer,
  result_bytes   integer,
  client_name    text,
  client_version text,
  user_agent     text,
  ip             text,
  session_id     text,
  transport      text
);
create index if not exists mcp_tool_calls_created_at_idx on public.mcp_tool_calls (created_at desc);
create index if not exists mcp_tool_calls_tool_idx on public.mcp_tool_calls (tool);

create table if not exists public.mcp_http_log (
  id            bigint generated always as identity primary key,
  created_at    timestamptz not null default now(),
  method        text,
  path          text,
  query         text,
  status        integer,
  duration_ms   integer,
  user_agent    text,
  ip            text,
  host          text,
  session_id    text,
  traffic_class text
);
create index if not exists mcp_http_log_created_at_idx on public.mcp_http_log (created_at desc);
create index if not exists mcp_http_log_class_idx on public.mcp_http_log (traffic_class);

-- Service-role key (used by the server) bypasses RLS; no public access.
alter table public.mcp_tool_calls enable row level security;
alter table public.mcp_http_log  enable row level security;
