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

app = FastAPI(title="Web Source Extractor Pro", version="10.0.3")

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

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
        Crash-proof:
        - If Playwright/Chromium fails on Vercel, return None (no crash).
        - Optional: Use remote browser if BROWSERLESS_WS is set.
        """
        if self.browser:
            return self.browser

        try:
            # import moved here => app won't crash at startup
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()

            # ✅ Best for Vercel: remote chromium (Browserless)
            browserless_ws = os.environ.get("BROWSERLESS_WS")
            if browserless_ws:
                # Example: wss://chrome.browserless.io?token=XXXX
                self.browser = await self.playwright.chromium.connect_over_cdp(browserless_ws)
                return self.browser

            # Local chromium (often fails on Vercel, but we catch errors)
            os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/tmp/playwright-browsers")
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
            context = await browser.new_context(ignore_https_errors=True)
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
        low = html.lower()
        bad = ["this is a trap for bots", "content loading...", "<body></body>"]
        return not any(x in low for x in bad)

    async def get_full_source(self, url: str):
        # InfinityFree
        if "infinityfree" in url.lower() or ".ifastnet" in url or ".epizy" in url:
            c, u = await self.bypass_infinityfree(url)
            if c:
                return c, u, "infinityfree"

        # HTTPX first
        c, u = await self.extract_with_httpx(url)
        if c and self.is_valid_content(c):
            return c, u, "httpx"

        # Playwright (optional)
        c, u = await self.extract_with_playwright(url)
        if c:
            return c, u, "playwright"

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
    return JSONResponse({"ok": True, "time": datetime.utcnow().isoformat()+"Z", "last_error": LAST_ERROR})


@app.get("/api/protected")
async def protected_extract(url: str = Query(..., description="URL to extract source from")):
    try:
        source_code, source_url, method = await extractor.get_full_source(url)

        if not source_code:
            raise HTTPException(
                status_code=404,
                detail={"message": "Could not extract source", "method": method, "last_error": LAST_ERROR},
            )

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