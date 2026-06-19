"""Supabase REST API client for Sage MCP Public.

Uses PostgREST (Supabase REST API) for all queries.
No direct database connections needed for read-only public data.
"""

import logging
from typing import Any, Optional

import httpx

from server.config import settings

logger = logging.getLogger("sage-mcp-public.db")

_http_client: Optional[httpx.AsyncClient] = None


async def get_client() -> httpx.AsyncClient:
    """Get or create the HTTP client for Supabase REST API."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            base_url=f"{settings.supabase_url}/rest/v1",
            headers={
                "apikey": settings.supabase_service_key,
                "Authorization": f"Bearer {settings.supabase_service_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        # Verify connectivity
        resp = await _http_client.get("/content?select=id&limit=1")
        resp.raise_for_status()
        logger.info("Supabase connection verified")
    return _http_client


async def query_table(
    table: str,
    select: str = "*",
    filters: dict[str, str] | None = None,
    order: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Query a table via PostgREST."""
    client = await get_client()
    params = {"select": select, "limit": str(limit)}
    if order:
        params["order"] = order
    if filters:
        params.update(filters)

    resp = await client.get(f"/{table}", params=params)
    resp.raise_for_status()
    return resp.json()


async def search_content(
    query: str,
    category: str | None = None,
    source: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Full-text search on content table."""
    client = await get_client()
    
    # Build PostgREST FTS query using websearch_to_tsquery (handles natural language)
    params = {
        "select": "slug,url,title,description,category,source,tags,author,publish_date",
        "fts": f"wfts(english).{query}",
        "limit": str(limit),
    }
    if category:
        params["category"] = f"eq.{category}"
    if source:
        params["source"] = f"eq.{source}"

    resp = await client.get("/content", params=params)
    if resp.status_code == 400:
        # Fallback to plain text search with ilike
        params.pop("fts")
        params["or"] = f"(title.ilike.*{query}*,body_text.ilike.*{query}*,description.ilike.*{query}*)"
        resp = await client.get("/content", params=params)
    
    resp.raise_for_status()
    return resp.json()


async def get_content_by_slug(slug: str) -> dict | None:
    """Get a single content page by slug."""
    client = await get_client()
    resp = await client.get(
        "/content",
        params={"select": "*", "slug": f"eq.{slug}", "limit": "1"},
    )
    resp.raise_for_status()
    data = resp.json()
    return data[0] if data else None


async def search_providers(
    query: str | None = None,
    state: str | None = None,
    modality: str | None = None,
    svi_only: bool = False,
    limit: int = 50,
) -> list[dict]:
    """Search providers with filters."""
    client = await get_client()
    params = {
        "select": "name,address,city,state,zip,phone,website,modalities,is_active,is_svi,is_mobile,is_verified,ownership_type,pe_brand,metro,google_rating,google_review_count,latitude,longitude,slug",
        "is_active": "eq.true",
        "limit": str(limit),
        "order": "google_rating.desc.nullslast",
    }
    
    if query:
        params["fts"] = f"wfts(english).{query}"
    
    if state:
        params["state"] = f"eq.{state.upper()}"
    
    if modality:
        params["modalities"] = f"cs.{{{modality}}}"
    
    if svi_only:
        params["is_svi"] = "eq.true"
    
    resp = await client.get("/providers", params=params)
    if resp.status_code == 400 and query:
        # Fallback to ilike
        params.pop("fts", None)
        params["or"] = f"(name.ilike.*{query}*,city.ilike.*{query}*,metro.ilike.*{query}*)"
        resp = await client.get("/providers", params=params)
    
    resp.raise_for_status()
    return resp.json()


async def get_provider_by_slug(slug: str) -> dict | None:
    """Get a single provider by slug."""
    client = await get_client()
    resp = await client.get(
        "/providers",
        params={"select": "*", "slug": f"eq.{slug}", "limit": "1"},
    )
    resp.raise_for_status()
    data = resp.json()
    return data[0] if data else None


async def get_pricing(category: str | None = None) -> list[dict]:
    """Get pricing data, optionally filtered by category."""
    params = {
        "select": "service_name,category,price_min,price_max,price_text,description,notes,location",
        "is_active": "eq.true",
        "order": "sort_order.asc",
    }
    if category:
        params["category"] = f"eq.{category}"
    
    return await query_table("pricing", **{k: v for k, v in params.items() if k == "select"}, filters={k: v for k, v in params.items() if k != "select"})


async def get_locations() -> list[dict]:
    """Get all SVI locations."""
    return await query_table("locations", select="*")


async def get_company_info(category: str | None = None) -> list[dict]:
    """Get company info entries."""
    filters = {}
    if category:
        filters["category"] = f"eq.{category}"
    return await query_table("company_info", filters=filters)


async def close():
    """Close the HTTP client."""
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None
