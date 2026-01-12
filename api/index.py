from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response, JSONResponse
from fastapi.templating import Jinja2Templates

import httpx
import asyncio
import time
from urllib.parse import urlparse
from datetime import datetime
from playwright.async_api import async_playwright
from pathlib import Path

app = FastAPI(
    title="Web Source Extractor Pro",
    description="Extract full source code from any website including JavaScript-rendered content",
    version="10.0.1"
)

# --- Templates (works on Vercel too) ---
BASE_DIR = Path(__file__).resolve().parents[1]  # project root (../)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class WebSourceExtractor:
    def __init__(self):
        self.browser = None
        self.playwright = None

    async def init_browser(self):
        """Initialize Playwright browser"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu",
                ],
            )
        return self.browser

    async def extract_with_playwright(self, url: str):
        """Extract content using headless browser for JS sites"""
        browser = await self.init_browser()

        try:
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                java_script_enabled=True,
                bypass_csp=False,
                ignore_https_errors=True,
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                },
            )

            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=60000)

            # wait for JS
            await asyncio.sleep(2)

            # trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            html = await page.content()
            final_url = page.url

            await context.close()
            return html, final_url

        except Exception:
            return None, None

    async def extract_with_httpx(self, url: str):
        """Try traditional HTTP extraction for static sites"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.text, str(response.url)

        except Exception:
            pass

        return None, None

    async def bypass_infinityfree(self, url: str):
        """Special bypass for InfinityFree protection"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }

            urls_to_try = [
                url,
                url.replace("https://", "http://"),
                url + "?i=1",
                url + "?nocache=1",
                url + f"?t={int(time.time())}",
            ]

            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                for test_url in urls_to_try:
                    try:
                        response = await client.get(test_url, headers=headers)
                        if response.status_code == 200:
                            content = response.text
                            if "aes.js" not in content and "slowAES.decrypt" not in content:
                                return content, test_url
                    except Exception:
                        continue

        except Exception:
            pass

        return None, None

    def is_valid_content(self, html: str):
        """Check if HTML contains actual content"""
        if not html or len(html.strip()) < 100:
            return False

        trap_indicators = [
            "This is a trap for bots",
            "Content loading...",
            "Please wait...",
            "Loading...",
            "<body></body>",
            "<body> </body>",
        ]

        html_low = html.lower()
        for indicator in trap_indicators:
            if indicator.lower() in html_low:
                return False

        return True

    async def get_full_source(self, url: str):
        """Main extraction method with multiple strategies"""
        # Method 1: InfinityFree
        if "infinityfree" in url.lower() or ".ifastnet" in url or ".epizy" in url:
            content, source_url = await self.bypass_infinityfree(url)
            if content:
                return content, source_url

        # Method 2: HTTPX
        content, source_url = await self.extract_with_httpx(url)
        if content and self.is_valid_content(content):
            return content, source_url

        # Method 3: Playwright
        content, source_url = await self.extract_with_playwright(url)
        if content:
            return content, source_url

        return None, None

    async def close(self):
        """Cleanup resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


extractor = WebSourceExtractor()


@app.get("/")
async def home(request: Request):
    # Render templates/index.html
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/protected")
async def protected_extract(url: str = Query(..., description="URL to extract source from")):
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        source_code, source_url = await extractor.get_full_source(url)

        if not source_code:
            raise HTTPException(
                status_code=404,
                detail="Could not extract source code. The website might be blocking automated access or requires JavaScript.",
            )

        clean_html = f"""<!--
Extracted from: {url}
Source URL: {source_url}
Time: {datetime.now().isoformat()}
Powered by: Web Source Extractor Pro
Developer: Haseeb Sahil
Note: This is the fully rendered HTML including JavaScript-generated content
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
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@app.get("/api/debug")
async def debug_url(url: str = Query(..., description="URL to debug")):
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)

            content = response.text
            headers = dict(response.headers)

            is_protected = "aes.js" in content or "slowAES.decrypt" in content
            has_js = "<script" in content.lower()

            return JSONResponse(
                {
                    "url": str(response.url),
                    "status_code": response.status_code,
                    "content_length": len(content),
                    "is_protected": is_protected,
                    "has_javascript": has_js,
                    "content_preview": content[:300] + "..." if len(content) > 300 else content,
                    "headers": {k: v for k, v in headers.items() if k.lower() not in ["set-cookie", "cookie"]},
                }
            )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.on_event("shutdown")
async def shutdown_event():
    await extractor.close()


# For local run
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)