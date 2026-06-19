# Sage MCP Public

Model Context Protocol server for Sage Veterinary Imaging's public data.

## What It Serves

| Table | Records | Description |
|-------|---------|-------------|
| `content` | 536 | Website pages, blog posts, conditions, education articles |
| `providers` | 808 | Veterinary imaging provider directory (40 states) |
| `pricing` | 33 | SVI imaging service pricing |
| `locations` | 3 | SVI facility details (Round Rock TX, Spring TX, Sandy UT) |

## MCP Tools

- `search_content` — Full-text search across all website content
- `get_page` — Get a specific page by URL slug
- `search_providers` — Search 800+ vet imaging facilities by location/modality
- `get_provider` — Provider detail by slug
- `get_pricing` — SVI service pricing, filterable by category
- `get_location_info` — SVI location details (address, phone, modalities)
- `get_company_info` — Company info, FAQs, policies
- `get_service_info` — Imaging service descriptions

## Architecture

```
GitHub → Railway (FastAPI + MCP) → Supabase (PostgreSQL + PostgREST)
```

- **No PHI.** Completely separate from the clinical MCP server.
- **Supabase REST API** for all queries (no direct DB connections needed).
- **Full-text search** via PostgreSQL tsvector indexes.

## Deployment

### Railway

1. Connect this repo to Railway
2. Set environment variables:
   - `SUPABASE_URL` — Supabase project URL
   - `SUPABASE_SERVICE_KEY` — Service role JWT
   - `PORT` — Railway sets this automatically

### Content Refresh

Run the sync worker to re-scrape website content:

```bash
python -m sync.refresh
```

Set up as a Railway cron service for weekly refresh.

## Local Development

```bash
pip install -r requirements.txt
cp .env.example .env  # Add your Supabase credentials
python -m server.main
```

Server runs at `http://localhost:8000`
- Health: `GET /health`
- MCP: `POST /mcp`
