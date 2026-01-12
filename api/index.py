from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response, JSONResponse
from fastapi.templating import Jinja2Templates

import httpx
import asyncio
import time
import os
import traceback
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

app = FastAPI(title="Web Source Extractor Pro", version="10.0.2")

# ---- templates path (works on Vercel) ----
BASE_DIR = Path(__file__).resolve().parents[1]  # project root
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ---- debug: store last runtime error ----
LAST_ERROR = {"where": None, "error": None, "trace": None, "time": None}

def set_last_error(where: str, e: Exception):
    LAST_ERROR["where"] = where
    LAST_ERROR["error"] = str(e)
    LAST_ERROR["trace"] = traceback.format_exc()
    LAST_ERROR["time"] = datetime.utcnow().isoformat() + "Z"


class WebSourceExtractor:
    def __init__(self):
        self.playwright = None
        self.browser = None

    async def init_browser(self):
        """
        Start Playwright lazily.
        If it fails on Vercel due to missing deps/binaries, we catch & fallback elsewhere.
        """
        if self.browser:
            return self.browser

        try:
            # recommended in serverless: keep browsers in writable temp
            # (doesn't guarantee deps exist, but avoids path issues)
            os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/tmp/playwright-browsers")

            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-zygote",
                    "--single-process",
                ],
            )
            return self.browser
        except Exception as e:
            set_last_error("init_browser", e)
            await self.close()
            return None

    async def extract_with_playwright(self, url: str):
        browser = await self.init_browser()
        if not browser:
            return None, None

        try:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                ignore_https_errors=True,
                java_script_enabled=True,
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=60000)

            await asyncio.sleep(2)
            html = await page.content()
            final_url = page.url

            await context.close()
            return html, final_url
        except Exception as e:
            set_last_error("extract_with_playwright", e)
            return None, None

    async def extract_with_httpx(self, url: str):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                r = await client.get(url, headers=headers)
                if r.status_code == 200:
                    return r.text, str(r.url)
        except Exception as e:
            set_last_error("extract_with_httpx", e)
        return None, None

    async def bypass_infinityfree(self, url: str):
        try:
            headers = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}
            urls_to_try = [
                url,
                url.replace("https://", "http://"),
                url + "?nocache=1",
                url + f"?t={int(time.time())}",
            ]
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                for test_url in urls_to_try:
                    try:
                        r = await client.get(test_url, headers=headers)
                        if r.status_code == 200:
                            c = r.text
                            if "aes.js" not in c and "slowAES.decrypt" not in c:
                                return c, str(r.url)
                    except Exception:
                        continue
        except Exception as e:
            set_last_error("bypass_infinityfree", e)
        return None, None

    def is_valid_content(self, html: str):
        if not html or len(html.strip()) < 100:
            return False
        bad = ["This is a trap for bots", "Content loading...", "<body></body>"]
        low = html.lower()
        return not any(x.lower() in low for x in bad)

    async def get_full_source(self, url: str):
        # InfinityFree first
        if "infinityfree" in url.lower() or ".ifastnet" in url or ".epizy" in url:
            content, u = await self.bypass_infinityfree(url)
            if content:
                return content, u, "infinityfree"

        # Try HTTPX first
        content, u = await self.extract_with_httpx(url)
        if content and self.is_valid_content(content):
            return content, u, "httpx"

        # Try Playwright (may fail on Vercel → fallback)
        content, u = await self.extract_with_playwright(url)
        if content:
            return content, u, "playwright"

        return None, None, "failed"

    async def close(self):
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        self.browser = None
        self.playwright = None


extractor = WebSourceExtractor()


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health():
    """
    If your function is crashing, hit /api/health first.
    It will show last captured error + env hints.
    """
    return JSONResponse(
        {
            "ok": True,
            "time": datetime.utcnow().isoformat() + "Z",
            "last_error": LAST_ERROR,
            "hints": {
                "playwright_browsers_path": os.environ.get("PLAYWRIGHT_BROWSERS_PATH"),
                "note": "If Playwright keeps failing on Vercel, use HTTPX-only or a remote browser (Browserless/ZenRows).",
            },
        }
    )


@app.get("/api/protected")
async def protected_extract(url: str = Query(..., description="URL to extract source from")):
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        source_code, source_url, method = await extractor.get_full_source(url)

        if not source_code:
            # return a readable error instead of crashing the whole function
            detail = {
                "message": "Could not extract source. Site may block bots or needs JS rendering.",
                "method": method,
                "last_error": LAST_ERROR,
            }
            raise HTTPException(status_code=404, detail=detail)

        clean_html = f"""<!--
Extracted from: {url}
Source URL: {source_url}
Time: {datetime.utcnow().isoformat()}Z
Method: {method}
-->

{source_code}
"""

        return Response(
            content=clean_html,
            media_type="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="extracted-{urlparse(url).netloc}.html"',
                "Content-Type": "text/html; charset=utf-8",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        set_last_error("protected_extract", e)
        raise HTTPException(status_code=500, detail={"message": "Internal error", "last_error": LAST_ERROR})


@app.get("/api/debug")
async def debug_url(url: str = Query(..., description="URL to debug")):
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            r = await client.get(url)
            content = r.text
            is_protected = "aes.js" in content or "slowAES.decrypt" in content
            has_js = "<script" in content.lower()
            return JSONResponse(
                {
                    "url": str(r.url),
                    "status_code": r.status_code,
                    "content_length": len(content),
                    "is_protected": is_protected,
                    "has_javascript": has_js,
                    "content_preview": content[:300] + "..." if len(content) > 300 else content,
                    "headers": {k: v for k, v in dict(r.headers).items() if k.lower() not in ["set-cookie", "cookie"]},
                }
            )
    except Exception as e:
        set_last_error("debug_url", e)
        return JSONResponse({"error": str(e), "last_error": LAST_ERROR}, status_code=500)


@app.on_event("shutdown")
async def shutdown_event():
    await extractor.close()