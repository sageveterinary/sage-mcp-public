"""Content refresh sync worker.

Re-scrapes website content and updates Supabase.
Designed to run as a daily cron job on Railway.

Usage:
    python -m sync.refresh
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sage-mcp-public.sync")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal,resolution=merge-duplicates",
}


def fetch_sitemap(base_url: str) -> list[str]:
    """Fetch URLs from sitemap.xml."""
    resp = httpx.get(f"{base_url}/sitemap.xml", timeout=30)
    urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
    return [u for u in urls if not u.endswith((".pdf", ".jpg", ".png"))]


def scrape_page(url: str) -> dict | None:
    """Scrape a single page via Squarespace JSON API, fallback to HTML."""
    try:
        # Try JSON endpoint first
        resp = httpx.get(f"{url}?format=json", timeout=15, follow_redirects=True)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/json"):
            data = resp.json()
            item = data.get("item") or data.get("collection") or data
            body = item.get("body", "") or ""

            # Clean HTML tags
            clean = re.sub(r"<[^>]+>", " ", body)
            clean = re.sub(r"\s+", " ", clean).strip()

            if len(clean) > 50:
                return {
                    "title": item.get("title", ""),
                    "description": (item.get("excerpt") or item.get("seoDescription") or "")[:2000],
                    "body_text": clean,
                    "author": (item.get("author", {}) or {}).get("displayName", ""),
                    "publish_date": None,
                    "tags": item.get("tags", []) or [],
                }

        # Fallback: scrape HTML
        resp = httpx.get(url, timeout=15, follow_redirects=True)
        if resp.status_code != 200:
            return None

        html = resp.text
        # Extract title
        title_match = re.search(r"<title>(.*?)</title>", html)
        title = title_match.group(1).strip() if title_match else ""

        # Extract meta description
        desc_match = re.search(r'<meta\s+name="description"\s+content="(.*?)"', html)
        desc = desc_match.group(1) if desc_match else ""

        # Extract main content
        main_match = re.search(r"<main[^>]*>(.*?)</main>", html, re.DOTALL)
        body_html = main_match.group(1) if main_match else html

        clean = re.sub(r"<script[^>]*>.*?</script>", "", body_html, flags=re.DOTALL)
        clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL)
        clean = re.sub(r"<[^>]+>", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        if len(clean) > 50:
            return {
                "title": title,
                "description": desc[:2000],
                "body_text": clean,
                "author": "",
                "publish_date": None,
                "tags": [],
            }

    except Exception as e:
        logger.warning(f"Error scraping {url}: {e}")

    return None


def categorize_url(url: str) -> str:
    """Categorize a URL based on its path."""
    path = url.split("//", 1)[-1].split("/", 1)[-1] if "/" in url else ""
    if "/blog/" in url or path.startswith("blog"):
        return "blog"
    if "conditions-we-diagnose" in url:
        return "condition"
    if "locations-we-serve" in url:
        return "location_page"
    if "online-radiology-education" in url or "ce-" in url:
        return "education"
    if "services" in url:
        return "service"
    return "page"


def url_to_slug(url: str, base_url: str) -> str:
    """Convert URL to slug."""
    slug = url.replace(base_url, "").strip("/")
    return slug or "home"


def sync_site(base_url: str, source: str):
    """Sync a single website."""
    logger.info(f"Syncing {source}...")

    urls = fetch_sitemap(base_url)
    logger.info(f"Found {len(urls)} URLs in sitemap")

    rows = []
    errors = 0

    for i, url in enumerate(urls):
        # Skip form/calendar pages
        if any(skip in url for skip in ["/form/", "/calendar/", "?format="]):
            continue

        page = scrape_page(url)
        if page:
            slug = url_to_slug(url, base_url)
            if source == "sageteleradiology.com":
                slug = f"telerad/{slug}"

            rows.append({
                "slug": slug,
                "url": url,
                "title": (page["title"] or "")[:500],
                "description": page["description"],
                "body_text": page["body_text"],
                "category": categorize_url(url),
                "source": source,
                "tags": page.get("tags", []) or [],
                "author": page.get("author") or None,
                "publish_date": page.get("publish_date"),
            })
        else:
            errors += 1

        if (i + 1) % 50 == 0:
            logger.info(f"  Scraped {i + 1}/{len(urls)} ({len(rows)} content, {errors} errors)")

        time.sleep(0.2)

    # Upsert to Supabase in batches
    inserted = 0
    for i in range(0, len(rows), 25):
        batch = rows[i:i + 25]
        resp = httpx.post(
            f"{SUPABASE_URL}/rest/v1/content",
            headers=HEADERS,
            json=batch,
            timeout=60,
        )
        if resp.status_code in [200, 201]:
            inserted += len(batch)
        else:
            logger.error(f"Batch insert error: {resp.status_code} {resp.text[:200]}")

    logger.info(f"✓ {source}: {inserted}/{len(rows)} upserted, {errors} scrape errors")

    # Log sync
    httpx.post(
        f"{SUPABASE_URL}/rest/v1/sync_log",
        headers={**HEADERS, "Prefer": "return=minimal"},
        json={
            "source": source,
            "records_synced": inserted,
            "status": "success" if errors == 0 else "partial",
            "error_message": f"{errors} scrape errors" if errors else None,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
        timeout=15,
    )

    return inserted


def main():
    """Run full content refresh."""
    logger.info("=" * 50)
    logger.info("SAGE MCP PUBLIC — Content Refresh")
    logger.info("=" * 50)

    total = 0
    total += sync_site("https://www.sageveterinary.com", "sageveterinary.com")
    total += sync_site("https://www.sageteleradiology.com", "sageteleradiology.com")

    logger.info(f"\nTotal: {total} pages synced")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
