from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response, JSONResponse
import httpx
import asyncio
import re
import time
from urllib.parse import urljoin, urlparse
from datetime import datetime

app = FastAPI(
    title="Web Source Extractor API",
    description="API to extract HTML source code from websites",
    version="1.0.0"
)

class SimpleExtractor:
    def __init__(self):
        self.client = None
    
    async def get_client(self):
        if not self.client:
            self.client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                }
            )
        return self.client
    
    async def fetch_url(self, url: str):
        """Fetch URL with multiple attempts"""
        client = await self.get_client()
        
        # Try different methods
        methods = [
            # Method 1: Direct fetch
            lambda: client.get(url),
            
            # Method 2: With timestamp to bypass cache
            lambda: client.get(url + f'?t={int(time.time())}'),
            
            # Method 3: Different user agent
            lambda: client.get(url, headers={'User-Agent': 'Googlebot/2.1 (+http://www.google.com/bot.html)'}),
            
            # Method 4: HTTP instead of HTTPS
            lambda: client.get(url.replace('https://', 'http://')) if url.startswith('https://') else None,
            
            # Method 5: With nocache parameter
            lambda: client.get(url + '?nocache=1'),
        ]
        
        for method in methods:
            try:
                response = await method()
                if response and response.status_code == 200:
                    content = response.text
                    
                    # Check if it's valid content (not a bot trap)
                    if self.is_valid_content(content):
                        return content, str(response.url)
            except:
                continue
        
        return None, None
    
    def is_valid_content(self, content: str):
        """Check if content is valid HTML and not a bot trap"""
        if not content or len(content.strip()) < 100:
            return False
        
        content_lower = content.lower()
        
        # Check for bot traps
        traps = [
            'this is a trap for bots',
            'content loading...',
            'please wait...',
            'you are being redirected',
            'loading...',
        ]
        
        for trap in traps:
            if trap in content_lower:
                return False
        
        # Check for basic HTML structure
        has_html_structure = (
            '<!doctype' in content_lower or 
            '<html' in content_lower or 
            '<body' in content_lower
        )
        
        return has_html_structure
    
    async def close(self):
        if self.client:
            await self.client.aclose()

extractor = SimpleExtractor()

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return JSONResponse({
        "message": "Web Source Extractor API",
        "endpoints": {
            "extract": "/api/protected?url=URL",
            "debug": "/api/debug?url=URL",
            "health": "/health"
        },
        "example": "/api/protected?url=https://example.com",
        "author": "Haseeb Sahil",
        "contact": "@HS_WebSource_Bot"
    })

@app.get("/api/protected")
async def extract_source(
    url: str = Query(..., description="URL to extract source from"),
    raw: bool = Query(False, description="Return raw response without headers")
):
    """
    Extract HTML source code from a website
    
    Example: /api/protected?url=https://zalim.kesug.com
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")
    
    # Add https:// if not present
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        source_code, source_url = await extractor.fetch_url(url)
        
        if not source_code:
            raise HTTPException(
                status_code=404,
                detail="Could not extract source code. The website might be protected or inaccessible."
            )
        
        # Add metadata as HTML comment
        metadata = f"""<!--
Source: {url}
Extracted URL: {source_url}
Time: {datetime.now().isoformat()}
Tool: Web Source Extractor API
-->
"""
        
        full_content = metadata + "\n" + source_code
        
        if raw:
            # Return as plain text
            return Response(
                content=full_content,
                media_type="text/plain",
                headers={
                    "Content-Type": "text/plain; charset=utf-8"
                }
            )
        else:
            # Return as downloadable HTML file
            filename = f"extracted-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
            
            return Response(
                content=full_content,
                media_type="text/html",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Content-Type": "text/html; charset=utf-8",
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/api/debug")
async def debug_url(url: str = Query(..., description="URL to debug")):
    """Debug a URL to see what's returned"""
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, follow_redirects=True)
            
            content = response.text[:1000]  # First 1000 chars
            
            analysis = {
                "url": str(response.url),
                "final_url": str(response.url),
                "status_code": response.status_code,
                "content_length": len(response.text),
                "content_preview": content + ("..." if len(response.text) > 1000 else ""),
                "headers": dict(response.headers),
                "has_protection": any(x in response.text.lower() for x in ['aes.js', 'slowaes.decrypt']),
                "is_bot_trap": any(x in response.text.lower() for x in [
                    'trap for bots', 
                    'content loading',
                    'please wait'
                ]),
            }
            
            return JSONResponse(analysis)
            
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.get("/test")
async def test_endpoint():
    """Test endpoint with example"""
    return JSONResponse({
        "message": "API is working",
        "test_urls": [
            "https://zalim.kesug.com",
            "https://example.com",
            "https://httpbin.org/html"
        ],
        "usage": "GET /api/protected?url=YOUR_URL"
    })

@app.on_event("shutdown")
async def shutdown_event():
    await extractor.close()

# For Vercel compatibility
async def handler(request):
    return app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)