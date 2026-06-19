"""
Sage MCP Public — Model Context Protocol Server

Exposes public company data (website content, provider directory,
pricing, locations) as MCP tools for AI agents, chatbots, and VAPI.

No PHI. No patient data. Fully public information only.
"""

import json
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Response
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from server.config import settings
from server import database as db

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("sage-mcp-public")

# ─── MCP Server ──────────────────────────────────────────────────────────────

mcp = FastMCP(
    "Sage MCP Public",
    instructions=(
        "Sage Veterinary Imaging public information server. "
        "Search website content, blog posts, educational articles, "
        "veterinary imaging provider directory (800+ facilities nationwide), "
        "SVI pricing, location info, and company details. "
        "NO patient data — public information only."
    ),
    host="0.0.0.0",
    port=settings.port,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


# ─── MCP Tools ───────────────────────────────────────────────────────────────


@mcp.tool()
async def search_content(
    query: str,
    category: str | None = None,
    source: str | None = None,
    limit: int = 10,
) -> str:
    """Search website content using full-text search.

    Searches across page titles, descriptions, and full body text from
    sageveterinary.com and sageteleradiology.com.

    Args:
        query: Search terms (e.g., "MRI brain tumor", "ultrasound pricing", "seizures")
        category: Filter by content type - "blog", "condition", "page",
                  "location_page", "education", "ce_event", "service" (optional)
        source: Filter by website - "sageveterinary.com" or "sageteleradiology.com" (optional)
        limit: Max results (default 10, max 50)
    """
    limit = min(limit, 50)
    results = await db.search_content(query, category=category, source=source, limit=limit)

    if not results:
        return json.dumps({"results": [], "count": 0, "message": f"No content found matching '{query}'"})

    return json.dumps({"results": results, "count": len(results)}, default=str)


@mcp.tool()
async def get_page(slug: str) -> str:
    """Get full content of a specific page by its URL slug.

    Args:
        slug: The URL slug (e.g., "faq", "pricing", "blog/pet-mri-austin-texas",
              "conditions-we-diagnose/brain-tumors")
    """
    page = await db.get_content_by_slug(slug)
    if not page:
        return json.dumps({"error": f"Page '{slug}' not found"})
    return json.dumps(page, default=str)


@mcp.tool()
async def search_providers(
    query: str | None = None,
    state: str | None = None,
    modality: str | None = None,
    svi_only: bool = False,
    limit: int = 20,
) -> str:
    """Search the veterinary imaging provider directory (800+ facilities).

    Find veterinary imaging centers by location, name, modality, or state.
    Includes Google ratings, contact info, modalities offered, and ownership data.

    Args:
        query: Search terms - name, city, or metro area (e.g., "Houston", "BluePearl") (optional)
        state: Two-letter state code filter (e.g., "TX", "CA", "UT") (optional)
        modality: Filter by imaging modality - "CT", "MRI", "Ultrasound", "Echocardiography" (optional)
        svi_only: If true, return only SVI (Sage Veterinary Imaging) locations (default false)
        limit: Max results (default 20, max 100)
    """
    limit = min(limit, 100)
    results = await db.search_providers(
        query=query, state=state, modality=modality, svi_only=svi_only, limit=limit
    )

    if not results:
        return json.dumps({"results": [], "count": 0, "message": "No providers found"})

    return json.dumps({"results": results, "count": len(results)}, default=str)


@mcp.tool()
async def get_provider(slug: str) -> str:
    """Get detailed info for a specific provider by slug.

    Args:
        slug: Provider slug (e.g., "sage-veterinary-imaging-round-rock-round-rock-tx")
    """
    provider = await db.get_provider_by_slug(slug)
    if not provider:
        return json.dumps({"error": f"Provider '{slug}' not found"})
    return json.dumps(provider, default=str)


@mcp.tool()
async def get_pricing(category: str | None = None) -> str:
    """Get SVI pricing for imaging services.

    Returns current pricing for all SVI imaging services including
    CT, MRI, Ultrasound, Echocardiography, and add-on fees.

    Args:
        category: Filter by service category (e.g., "CT", "MRI",
                  "Ultrasound & Echo", "Neurology", "Add-ons") (optional)
    """
    results = await db.get_pricing(category=category)
    return json.dumps({"pricing": results, "count": len(results)}, default=str)


@mcp.tool()
async def get_location_info(slug: str | None = None) -> str:
    """Get SVI location details (address, phone, hours, modalities).

    Args:
        slug: Location slug for a specific location (e.g., "svi-round-rock-texas").
              If omitted, returns all 3 SVI locations.
    """
    if slug:
        locations = await db.query_table("locations", filters={"slug": f"eq.{slug}"})
        if not locations:
            return json.dumps({"error": f"Location '{slug}' not found"})
        return json.dumps(locations[0], default=str)
    else:
        locations = await db.get_locations()
        return json.dumps({"locations": locations, "count": len(locations)}, default=str)


@mcp.tool()
async def get_company_info(category: str | None = None) -> str:
    """Get company information, FAQs, and policies.

    Args:
        category: Filter by info category - "general", "faq", "policy",
                  "team", "history" (optional)
    """
    results = await db.get_company_info(category=category)
    if not results:
        return json.dumps({"info": [], "message": "No company info found for this category"})
    return json.dumps({"info": results, "count": len(results)}, default=str)


@mcp.tool()
async def get_service_info(service: str | None = None) -> str:
    """Get information about SVI's imaging services.

    Args:
        service: Service slug (e.g., "veterinary-mri", "veterinary-ct",
                 "veterinary-ultrasound"). If omitted, returns all services.
    """
    if service:
        # Search content for service pages
        results = await db.search_content(service, category="service", limit=5)
    else:
        results = await db.query_table(
            "content",
            select="slug,url,title,description,body_text",
            filters={"category": "eq.service"},
        )

    return json.dumps({"services": results, "count": len(results)}, default=str)


# ─── FastAPI App (health + MCP mount) ────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and clean up resources."""
    logger.info("Starting Sage MCP Public server...")
    await db.get_client()
    logger.info("Database connection established")
    yield
    await db.close()
    logger.info("Server shutting down")


app = FastAPI(
    title="Sage MCP Public",
    description="Public company data MCP server for Sage Veterinary Imaging",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        client = await db.get_client()
        resp = await client.get("/content?select=id&limit=1")
        db_ok = resp.status_code == 200
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "sage-mcp-public",
        "database": "connected" if db_ok else "disconnected",
    }


# Mount MCP at /mcp (SSE transport — proven stable with Railway)
mcp_app = mcp.sse_app()
app.mount("/mcp", mcp_app)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.port))
    uvicorn.run(app, host="0.0.0.0", port=port)
