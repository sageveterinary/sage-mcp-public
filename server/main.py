"""
Sage MCP Public — Model Context Protocol Server

Exposes public company data (website content, provider directory,
pricing, locations, clinical decision support, proximity search)
as MCP tools for AI agents, chatbots, and VAPI.

No PHI. No patient data. Fully public information only.
"""

import json
import logging
import math
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Response
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from server.config import settings
from server import database as db
from server.radiology_engine import (
    search_symptoms,
    get_recommendation,
    list_available_symptoms,
    ALL_SIGN_IDS,
    PRICING,
)

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("sage-mcp-public")

# ─── MCP Server ──────────────────────────────────────────────────────────────

mcp = FastMCP(
    "Sage MCP Public",
    instructions=(
        "Sage Veterinary Imaging public information server. "
        "Search website content, blog posts, educational articles, "
        "veterinary imaging provider directory (800+ facilities nationwide), "
        "SVI pricing, location info, company details, "
        "clinical decision support (symptom → imaging recommendation), "
        "nearest provider finder with distance, and structured price estimates. "
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


# ─── New Tools: Clinical Decision Support, Proximity Finder, Price Estimator ──


@mcp.tool()
async def clinical_decision_support(
    symptoms: str | None = None,
    symptom_ids: list[str] | None = None,
    species: str = "dog",
    breed: str = "",
    urgency: str = "standard",
    bilateral: bool = False,
    body_regions: list[str] | None = None,
) -> str:
    """Get imaging recommendations based on clinical signs and symptoms.

    Accepts either natural language symptom descriptions OR specific symptom IDs.
    Returns the recommended imaging modality, body regions, pricing estimate,
    clinical rationale, breed-specific alerts, and what's included.

    This is SVI's clinical decision support engine — the same algorithm used
    on FindVetImaging.com's imaging recommender tool.

    Args:
        symptoms: Natural language description of symptoms (e.g., "my dog is limping
                  and has back pain", "seizures", "abdominal mass"). The engine
                  maps these to clinical signs automatically.
        symptom_ids: List of specific clinical sign IDs (e.g., ["seizures", "back_pain"]).
                     Use list_clinical_signs to see all available IDs.
                     If both symptoms and symptom_ids are provided, they are combined.
        species: "dog" or "cat" (default "dog")
        breed: Breed name for breed-specific alerts (e.g., "French Bulldog", "Dachshund")
        urgency: "standard", "urgent", or "stat" — affects pricing (STAT fee added)
        bilateral: True if symptoms are bilateral (e.g., both elbows) — adds extra site
        body_regions: Optional list of body region IDs to override the engine's automatic
                      region selection. Use list_clinical_signs to see available regions.
    """
    # Collect tags from both natural language and explicit IDs
    tags: set[str] = set()
    if symptoms:
        tags = search_symptoms(symptoms)
    if symptom_ids:
        tags.update(sid for sid in symptom_ids if sid in ALL_SIGN_IDS)

    if not tags:
        available = list_available_symptoms()
        return json.dumps({
            "error": "No recognizable symptoms found. Provide symptom descriptions or valid symptom_ids.",
            "tip": "Try descriptions like 'seizures', 'back pain', 'limping', 'mass', 'vomiting'.",
            "available_sign_groups": available,
        })

    rec = get_recommendation(
        tags=list(tags),
        breed=breed,
        species=species,
        urgency=urgency,
        bilateral=bilateral,
        body_regions=body_regions,
    )

    result = rec.to_dict()
    result["matched_symptoms"] = sorted(tags)
    result["input_symptoms"] = symptoms or ""
    result["species"] = species
    result["breed"] = breed

    return json.dumps(result, default=str)


@mcp.tool()
async def list_clinical_signs() -> str:
    """List all available clinical signs and body regions for the decision support tool.

    Use this to discover valid symptom_ids and body_region IDs
    for the clinical_decision_support tool.
    """
    signs = list_available_symptoms()
    regions = [
        {"id": "head_brain", "label": "Head (brain)"},
        {"id": "head_nasal", "label": "Head (nasal / sinus)"},
        {"id": "head_ear", "label": "Head (tympanic bulla)"},
        {"id": "head_oral", "label": "Head (oral / mandible)"},
        {"id": "c_spine", "label": "C-spine"},
        {"id": "tl_spine", "label": "T-L spine"},
        {"id": "ls_spine", "label": "L-S spine / pelvis"},
        {"id": "shoulder", "label": "Shoulder"},
        {"id": "elbow", "label": "Elbow"},
        {"id": "forelimb", "label": "Thoracic limb (distal)"},
        {"id": "hip", "label": "Hip"},
        {"id": "stifle", "label": "Stifle"},
        {"id": "hindlimb", "label": "Pelvic limb (distal)"},
        {"id": "thorax", "label": "Thorax"},
        {"id": "abdomen", "label": "Abdomen"},
        {"id": "neck_soft", "label": "Cervical soft tissue"},
    ]
    return json.dumps({"clinical_sign_groups": signs, "body_regions": regions})


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in miles between two lat/lng points."""
    R = 3959  # Earth radius in miles
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── US Zip code → approximate lat/lng (top 500 3-digit prefixes) ──
# This is a lightweight geocoding fallback. For precise geocoding,
# use Google Maps Platform API.
_ZIP_PREFIX_COORDS: dict[str, tuple[float, float]] = {
    # Texas
    "787": (30.27, -97.74), "786": (30.51, -97.82), "785": (30.63, -97.69),
    "770": (29.76, -95.37), "773": (29.95, -95.40), "774": (29.58, -95.10),
    "750": (32.78, -96.80), "751": (32.80, -96.63), "752": (32.85, -96.85),
    "760": (32.73, -97.33), "761": (32.75, -97.35), "762": (32.73, -97.33),
    "782": (27.80, -97.40), "783": (27.50, -97.52), "784": (27.76, -97.43),
    "780": (29.42, -98.49), "781": (29.55, -98.55), "789": (29.38, -98.62),
    "765": (31.47, -97.19), "766": (31.55, -97.15), "768": (31.99, -102.11),
    "790": (33.58, -101.84), "791": (33.45, -101.85), "793": (33.47, -101.83),
    "795": (35.20, -101.83), "796": (35.08, -101.92), "797": (30.45, -104.02),
    "799": (31.76, -106.49),
    # Utah
    "840": (40.76, -111.89), "841": (40.77, -111.93), "843": (41.22, -111.97),
    "844": (40.23, -111.66), "845": (38.57, -109.55), "846": (39.60, -110.81),
    "847": (41.73, -111.83),
    # California
    "900": (34.05, -118.24), "901": (34.10, -118.33), "902": (33.93, -118.28),
    "903": (33.90, -118.05), "904": (33.82, -118.15), "906": (34.09, -118.00),
    "910": (91.10, -118.30), "911": (34.14, -118.26), "912": (34.17, -118.59),
    "913": (34.30, -118.45), "914": (34.42, -118.53), "915": (34.55, -118.12),
    "920": (32.72, -117.16), "921": (32.78, -117.15), "922": (33.95, -116.55),
    "925": (33.75, -116.97), "926": (33.80, -117.88), "927": (33.68, -117.84),
    "930": (34.42, -119.70), "931": (34.95, -120.43), "932": (35.37, -119.02),
    "933": (35.38, -119.02), "934": (34.28, -118.88), "935": (36.74, -119.77),
    "936": (36.74, -119.77), "937": (36.97, -121.95), "939": (37.34, -121.89),
    "940": (37.77, -122.42), "941": (37.77, -122.42), "942": (37.70, -122.47),
    "943": (37.56, -122.27), "944": (37.43, -122.14), "945": (37.80, -122.27),
    "946": (37.87, -122.27), "947": (37.97, -122.03), "948": (37.93, -122.35),
    "949": (37.95, -122.35), "950": (37.34, -121.89), "951": (33.95, -117.40),
    "952": (33.83, -117.57), "953": (33.91, -117.55), "954": (33.75, -117.87),
    "955": (39.73, -121.84), "956": (38.58, -121.49), "957": (38.55, -121.44),
    "958": (38.44, -122.71), "959": (38.78, -120.53), "960": (40.59, -122.39),
    "961": (41.73, -122.63),
    # Florida
    "320": (28.54, -81.38), "321": (28.36, -81.45), "322": (30.33, -81.66),
    "323": (30.44, -81.56), "324": (30.12, -82.31), "325": (27.95, -82.46),
    "326": (29.19, -82.14), "327": (28.50, -81.35), "328": (28.07, -80.62),
    "329": (25.78, -80.23), "330": (25.77, -80.19), "331": (26.19, -80.25),
    "332": (26.12, -80.14), "333": (25.76, -80.19), "334": (26.71, -80.05),
    "335": (27.34, -82.53), "336": (27.95, -82.46), "337": (27.64, -82.63),
    "338": (27.50, -82.55), "339": (27.34, -82.53), "341": (27.08, -82.43),
    "342": (26.64, -81.87), "344": (26.19, -80.25), "346": (27.95, -82.46),
    # New York
    "100": (40.71, -74.01), "101": (40.71, -74.01), "102": (40.71, -74.01),
    "103": (40.58, -74.15), "104": (40.65, -73.95), "105": (40.93, -73.78),
    "106": (41.03, -73.76), "107": (41.13, -73.79), "108": (41.18, -73.20),
    "109": (41.00, -73.87), "110": (40.68, -73.53), "111": (40.72, -73.46),
    "112": (40.65, -73.95), "113": (40.75, -73.87), "114": (40.75, -73.87),
    "115": (40.68, -73.53), "116": (40.72, -73.46), "117": (40.73, -73.21),
    "118": (40.93, -72.64), "119": (40.93, -72.64),
    "120": (42.65, -73.76), "121": (42.31, -73.88), "122": (42.18, -73.20),
    "123": (42.44, -73.26), "124": (42.09, -75.91), "125": (41.70, -73.93),
    "126": (41.50, -74.01), "127": (42.10, -75.91), "128": (42.82, -73.94),
    "130": (43.05, -76.15), "131": (43.05, -76.15), "132": (43.10, -75.23),
    "133": (42.10, -75.91), "134": (42.44, -76.50), "135": (43.11, -76.07),
    "136": (43.98, -75.91), "137": (43.80, -76.06), "140": (42.89, -78.88),
    "141": (42.89, -78.88), "142": (42.75, -78.72), "143": (42.09, -79.24),
    "144": (43.16, -77.62), "145": (43.16, -77.62), "146": (43.16, -77.62),
    "147": (42.45, -76.48), "148": (42.10, -76.82), "149": (43.13, -77.63),
    # Other major metros
    "600": (41.88, -87.63), "601": (41.85, -87.65), "602": (42.00, -87.68),
    "603": (41.72, -87.75), "604": (42.05, -88.05), "605": (42.09, -87.85),
    "606": (41.88, -87.63), "607": (42.00, -87.86),
    "200": (38.91, -77.04), "201": (38.98, -76.93), "202": (38.91, -77.04),
    "203": (38.91, -77.04), "204": (38.91, -77.04), "205": (38.91, -77.04),
    "206": (38.85, -77.31), "207": (38.90, -76.98),
    "300": (33.75, -84.39), "301": (33.77, -84.38), "302": (33.65, -84.43),
    "303": (33.81, -84.42),
    "480": (42.33, -83.05), "481": (42.33, -83.05), "482": (42.47, -83.15),
    "483": (42.72, -83.00), "484": (42.49, -83.48), "485": (42.49, -83.14),
    "430": (39.96, -82.99), "431": (39.96, -82.99), "432": (40.00, -83.02),
    "440": (41.50, -81.69), "441": (41.50, -81.69), "442": (41.08, -81.52),
    "443": (41.16, -81.44), "444": (41.08, -81.52), "445": (39.76, -84.19),
    "450": (39.10, -84.51), "451": (39.10, -84.51), "452": (39.10, -84.51),
    "453": (39.76, -84.19), "454": (39.76, -84.19),
    "190": (39.95, -75.17), "191": (39.95, -75.17), "192": (39.87, -75.52),
    "193": (40.24, -75.28), "194": (40.13, -75.52), "195": (40.37, -75.49),
    "550": (44.98, -93.27), "551": (44.95, -93.09), "553": (44.98, -93.27),
    "554": (44.93, -93.21), "555": (44.98, -93.27), "556": (46.87, -96.77),
    "570": (43.55, -96.73), "571": (43.55, -96.73),
    "730": (35.47, -97.52), "731": (36.15, -95.99), "732": (36.15, -95.99),
    "733": (35.47, -97.52), "734": (35.47, -97.52),
    "802": (39.74, -104.99), "803": (39.74, -104.99), "804": (39.87, -104.67),
    "805": (39.74, -105.00), "806": (39.62, -104.90), "808": (38.83, -104.82),
    "809": (38.55, -106.97),
    "980": (47.61, -122.33), "981": (47.61, -122.33), "982": (47.53, -122.62),
    "983": (47.25, -122.44), "984": (47.61, -122.33), "985": (47.98, -122.20),
    "970": (45.52, -122.68), "971": (45.52, -122.68), "972": (45.52, -122.68),
    "973": (44.94, -123.03), "974": (44.05, -123.09),
    "850": (33.45, -112.07), "851": (33.45, -112.07), "852": (33.45, -112.07),
    "853": (33.37, -111.72), "855": (34.50, -114.37), "856": (32.22, -110.97),
    "857": (32.22, -110.97),
    "890": (36.17, -115.14), "891": (36.17, -115.14),
    "027": (41.82, -71.41), "028": (41.82, -71.41), "029": (41.82, -71.41),
    "020": (42.36, -71.06), "021": (42.36, -71.06), "022": (42.38, -71.12),
    "023": (42.07, -71.02), "024": (42.47, -71.27),
}


def _zip_to_coords(zip_code: str) -> tuple[float, float] | None:
    """Convert a US zip code to approximate lat/lng using prefix lookup."""
    z = zip_code.strip().replace("-", "")[:5]
    if len(z) < 3:
        return None
    prefix = z[:3]
    return _ZIP_PREFIX_COORDS.get(prefix)


@mcp.tool()
async def find_nearest_provider(
    latitude: float | None = None,
    longitude: float | None = None,
    zip_code: str | None = None,
    city: str | None = None,
    state: str | None = None,
    modality: str | None = None,
    radius_miles: float = 100,
    svi_only: bool = False,
    limit: int = 10,
) -> str:
    """Find the nearest veterinary imaging providers to a location.

    Provide EITHER lat/lng coordinates OR a zip code OR a city+state.
    Returns providers sorted by distance with contact info, modalities,
    ratings, and distance in miles.

    Args:
        latitude: Latitude of search origin (preferred — most accurate)
        longitude: Longitude of search origin
        zip_code: US zip code to search from (approximate — uses centroid)
        city: City name to search from (combine with state for best results)
        state: Two-letter state code (e.g., "TX", "CA")
        modality: Filter by imaging capability - "CT", "MRI", "Ultrasound", "Echocardiography"
        radius_miles: Search radius in miles (default 100, max 500)
        svi_only: If true, only return Sage Veterinary Imaging locations
        limit: Max results (default 10, max 50)
    """
    radius_miles = min(radius_miles, 500)
    limit = min(limit, 50)

    # Resolve coordinates
    lat, lng = latitude, longitude
    if lat is None or lng is None:
        if zip_code:
            coords = _zip_to_coords(zip_code)
            if coords:
                lat, lng = coords
        if (lat is None or lng is None) and city:
            # Fall back to text search if no coords
            results = await db.search_providers(
                query=f"{city} {state}" if state else city,
                state=state,
                modality=modality,
                svi_only=svi_only,
                limit=limit,
            )
            return json.dumps({
                "results": results,
                "count": len(results),
                "search_method": "text_search",
                "note": "Could not geocode location. Results are text-matched, not distance-sorted.",
            }, default=str)

    if lat is None or lng is None:
        return json.dumps({
            "error": "Could not determine location. Provide latitude/longitude, a valid US zip code, or city+state.",
        })

    # Fetch all active providers with coordinates
    fetch_limit = 500  # Get enough to filter
    params: dict[str, str] = {
        "select": "name,address,city,state,zip,phone,website,modalities,is_active,is_svi,is_mobile,is_verified,ownership_type,pe_brand,metro,google_rating,google_review_count,latitude,longitude,slug",
        "is_active": "eq.true",
        "latitude": "not.is.null",
        "longitude": "not.is.null",
        "limit": str(fetch_limit),
    }
    if modality:
        params["modalities"] = f"cs.{{{modality}}}"
    if svi_only:
        params["is_svi"] = "eq.true"
    if state:
        params["state"] = f"eq.{state.upper()}"

    client = await db.get_client()
    resp = await client.get("/providers", params=params)
    resp.raise_for_status()
    providers = resp.json()

    # Calculate distances and filter by radius
    for p in providers:
        if p.get("latitude") and p.get("longitude"):
            p["distance_miles"] = round(
                _haversine(lat, lng, p["latitude"], p["longitude"]), 1
            )
        else:
            p["distance_miles"] = None

    # Filter by radius and sort by distance
    within_radius = [
        p for p in providers
        if p["distance_miles"] is not None and p["distance_miles"] <= radius_miles
    ]
    within_radius.sort(key=lambda p: p["distance_miles"])
    within_radius = within_radius[:limit]

    # Clean up output
    for p in within_radius:
        p.pop("latitude", None)
        p.pop("longitude", None)

    return json.dumps({
        "results": within_radius,
        "count": len(within_radius),
        "search_origin": {"latitude": lat, "longitude": lng},
        "radius_miles": radius_miles,
        "search_method": "proximity",
    }, default=str)


@mcp.tool()
async def estimate_price(
    modality: str,
    sites: int = 1,
    contrast: bool = False,
    urgency: str = "standard",
    combo_echo_us: bool = False,
) -> str:
    """Get a structured price estimate for SVI imaging services.

    Returns detailed pricing breakdown with line items, what's included,
    bloodwork requirements, and duration estimate.

    Args:
        modality: Imaging modality - "MRI", "CT", "Ultrasound", "Echocardiogram"
        sites: Number of body regions/sites to image (default 1). For MRI: each
               additional site after the first adds $950. For CT: $595 per additional site.
        contrast: Whether IV contrast is needed (applies to CT — adds $365 to base)
        urgency: "standard", "urgent", or "stat" — STAT adds a rush fee
        combo_echo_us: If true, uses combo Echo + Abdominal US pricing ($1,485)
    """
    modality_upper = modality.upper().strip()
    sites = max(1, min(sites, 5))

    result: dict = {
        "modality": modality,
        "sites": sites,
        "urgency": urgency,
    }

    if "MRI" in modality_upper:
        base = PRICING["mri_pkg"]
        additional = (sites - 1) * PRICING["mri_add"]
        price = base + additional
        result["base_price"] = base
        result["base_label"] = f"MRI Package (includes bloodwork) — ${base:,}"
        if sites > 1:
            result["additional_sites"] = f"{sites - 1} additional site(s) × ${PRICING['mri_add']:,} = ${additional:,}"
        result["bloodwork"] = "Required — CBC + Chem within 30 days. Included in MRI Package price."
        result["bloodwork_note"] = f"If patient has qualifying labs on file, base MRI price (${PRICING['mri1']:,}) applies instead of package."
        result["included"] = [
            "3T MRI scanner", "General anesthesia + monitoring",
            "IV catheter + fluids", "DACVR on-site interpretation",
            "Direct call to rDVM same day", "Written report within 24 hrs",
            "Same-day discharge",
        ]
        result["duration"] = "2–4 hours (scan + recovery)"

    elif "CT" in modality_upper:
        base = PRICING["ct_con"] if contrast else PRICING["ct"]
        additional = (sites - 1) * PRICING["ct_add"]
        price = base + additional
        result["contrast"] = contrast
        result["base_price"] = base
        result["base_label"] = f"CT {'with contrast' if contrast else 'non-contrast'} — ${base:,}"
        if sites > 1:
            result["additional_sites"] = f"{sites - 1} additional site(s) × ${PRICING['ct_add']:,} = ${additional:,}"
        result["bloodwork"] = "Required — Chem 10 minimum within 30 days"
        result["bloodwork_note"] = f"In-house bloodwork available (${PRICING['bw']}). If patient has qualifying labs, send with referral."
        result["included"] = [
            "128-slice CT scanner",
            "IV contrast study" if contrast else "Non-contrast",
            "General anesthesia + monitoring",
            "DACVR on-site interpretation",
            "Direct call to rDVM same day",
            "Written report within 24 hrs",
            "Same-day discharge",
        ]
        result["duration"] = "1.5–2.5 hours"

    elif "ULTRA" in modality_upper or "US" == modality_upper:
        base = PRICING["us"]
        additional = (sites - 1) * PRICING["us_add"]
        price = base + additional
        result["base_price"] = base
        result["base_label"] = f"Abdominal Ultrasound — ${base:,}"
        if sites > 1:
            result["additional_sites"] = f"{sites - 1} additional site(s) × ${PRICING['us_add']:,} = ${additional:,}"
        result["bloodwork"] = "Not required — light sedation, no general anesthesia"
        result["included"] = [
            "Complete abdominal US", "Light sedation PRN",
            "DACVR on-site", "Report within 24 hrs",
            "30–60 min appointment", "No general anesthesia",
        ]
        result["duration"] = "30–60 minutes"

    elif "ECHO" in modality_upper:
        if combo_echo_us:
            price = PRICING["echo_us"]
            result["base_price"] = price
            result["base_label"] = f"Echo + Abdominal US combo — ${price:,}"
            result["included"] = [
                "Full echocardiogram", "Complete abdominal ultrasound",
                "DACVR + cardiologist interpretation",
                "Report within 24 hrs", "No sedation required",
                "30–60 min appointment",
            ]
        else:
            price = PRICING["echo"]
            result["base_price"] = price
            result["base_label"] = f"Echocardiogram — ${price:,}"
            result["included"] = [
                "Full echocardiogram",
                "DACVR + cardiologist interpretation",
                "Report within 24 hrs", "No sedation required",
                "30–60 min appointment",
            ]
        result["bloodwork"] = "Not required — no general anesthesia"
        result["duration"] = "30–60 minutes"

    else:
        return json.dumps({
            "error": f"Unknown modality '{modality}'. Valid options: MRI, CT, Ultrasound, Echocardiogram",
        })

    # STAT fee
    stat_fee = 0
    if urgency == "stat":
        if "MRI" in modality_upper:
            stat_fee = PRICING["stat_mri"]
        elif "CT" in modality_upper:
            stat_fee = PRICING["stat_ct"]
        else:
            stat_fee = PRICING["stat_us"]
        price += stat_fee
        result["stat_fee"] = f"STAT rush fee — ${stat_fee:,}"

    result["total_estimate"] = f"${price:,}"
    result["total_amount"] = price
    result["note"] = "Prices are estimates for SVI locations. Final pricing confirmed at scheduling. All studies interpreted by board-certified veterinary radiologists (DACVR) on-site."

    return json.dumps(result, default=str)


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


@app.get("/.well-known/mcp.json")
async def mcp_discovery():
    """MCP discovery endpoint — tells AI agents where to find this MCP server."""
    return {
        "mcp_version": "2025-03-26",
        "name": "Sage Veterinary Imaging",
        "description": (
            "Public MCP server for Sage Veterinary Imaging — "
            "veterinary diagnostic imaging services, 800+ provider directory, "
            "pricing, locations, educational content, and clinical resources. "
            "No patient data. Fully public."
        ),
        "url": "https://mcp.sageveterinary.com/mcp",
        "transport": {
            "type": "sse",
            "url": "https://mcp.sageveterinary.com/mcp/sse",
        },
        "capabilities": {
            "tools": True,
            "resources": False,
            "prompts": False,
        },
        "tool_count": 12,
        "authentication": None,
        "contact": {
            "website": "https://www.sageveterinary.com",
            "email": "support@sageveterinary.com",
        },
    }


@app.get("/.well-known/mcp/server-card.json")
async def smithery_server_card():
    """Smithery server-card.json — static metadata for registry indexing.

    Smithery uses this to skip automatic scanning when it can't connect
    via the MCP transport directly. See: https://smithery.ai/docs/build/publish
    """
    return {
        "serverInfo": {
            "name": "Sage Veterinary Imaging MCP",
            "version": "1.0.0",
        },
        "authentication": {
            "required": False,
        },
        "tools": [
            {
                "name": "search_content",
                "description": "Full-text search across 500+ pages of website content, blog posts, and educational articles from sageveterinary.com and sageteleradiology.com.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search terms"},
                        "category": {"type": "string", "description": "Filter by content type"},
                        "source": {"type": "string", "description": "Filter by website"},
                        "limit": {"type": "integer", "description": "Max results (default 10)"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_page",
                "description": "Get full content of a specific page by its URL slug.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "slug": {"type": "string", "description": "URL slug of the page"},
                    },
                    "required": ["slug"],
                },
            },
            {
                "name": "search_providers",
                "description": "Search the veterinary imaging provider directory (800+ facilities across 41 states).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Name, city, or metro area"},
                        "state": {"type": "string", "description": "Two-letter state code"},
                        "modality": {"type": "string", "description": "CT, MRI, Ultrasound, Echocardiography"},
                        "svi_only": {"type": "boolean", "description": "Only SVI locations"},
                        "limit": {"type": "integer", "description": "Max results (default 20)"},
                    },
                },
            },
            {
                "name": "get_provider",
                "description": "Get detailed info for a specific provider by slug.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "slug": {"type": "string", "description": "Provider slug"},
                    },
                    "required": ["slug"],
                },
            },
            {
                "name": "get_pricing",
                "description": "Get current SVI pricing for all imaging services.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Filter by service category"},
                    },
                },
            },
            {
                "name": "get_location_info",
                "description": "Get SVI location details — address, phone, hours, modalities.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "slug": {"type": "string", "description": "Location slug (omit for all 3)"},
                    },
                },
            },
            {
                "name": "get_company_info",
                "description": "Get company information, FAQs, and policies.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Filter by info category"},
                    },
                },
            },
            {
                "name": "get_service_info",
                "description": "Get information about SVI imaging services.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service": {"type": "string", "description": "Service slug (omit for all)"},
                    },
                },
            },
            {
                "name": "clinical_decision_support",
                "description": "Get imaging recommendations based on clinical signs and symptoms. Returns modality, body regions, pricing, and clinical rationale.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "symptoms": {"type": "string", "description": "Natural language symptom description"},
                        "symptom_ids": {"type": "array", "items": {"type": "string"}, "description": "Specific clinical sign IDs"},
                        "species": {"type": "string", "description": "dog or cat"},
                        "breed": {"type": "string", "description": "Breed name for breed-specific alerts"},
                        "urgency": {"type": "string", "description": "standard, urgent, or stat"},
                    },
                },
            },
            {
                "name": "list_clinical_signs",
                "description": "List all available clinical signs and body regions for the decision support tool.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "find_nearest_provider",
                "description": "Find the nearest veterinary imaging providers to a location. Input zip code, city+state, or lat/lng.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "zip_code": {"type": "string", "description": "US zip code"},
                        "city": {"type": "string", "description": "City name"},
                        "state": {"type": "string", "description": "Two-letter state code"},
                        "latitude": {"type": "number", "description": "Latitude"},
                        "longitude": {"type": "number", "description": "Longitude"},
                        "modality": {"type": "string", "description": "Filter by modality"},
                        "radius_miles": {"type": "number", "description": "Search radius (default 100)"},
                        "limit": {"type": "integer", "description": "Max results (default 10)"},
                    },
                },
            },
            {
                "name": "estimate_price",
                "description": "Get a structured price estimate for SVI imaging services with line-item breakdown.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "modality": {"type": "string", "description": "MRI, CT, Ultrasound, or Echocardiogram"},
                        "sites": {"type": "integer", "description": "Number of body regions (default 1)"},
                        "contrast": {"type": "boolean", "description": "Whether IV contrast is needed"},
                        "urgency": {"type": "string", "description": "standard, urgent, or stat"},
                    },
                    "required": ["modality"],
                },
            },
        ],
        "resources": [],
        "prompts": [],
    }


# Mount MCP at /mcp (SSE transport — proven stable with Railway)
mcp_app = mcp.sse_app()
app.mount("/mcp", mcp_app)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.port))
    uvicorn.run(app, host="0.0.0.0", port=port)
