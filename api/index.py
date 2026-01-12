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
    description="API to extract source code from websites",
    version="1.0.0"
)

class SourceExtractor:
    def __init__(self):
        self.session = None
        
    async def get_session(self):
        if not self.session:
            self.session = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
        return self.session
        
    async def fetch_with_protection_bypass(self, url: str):
        """Try to bypass website protections"""
        session = await self.get_session()
        
        # First try direct fetch
        try:
            response = await session.get(url)
            content = response.text
            
            # Check if it's protected (InfinityFree or similar)
            if 'aes.js' in content or 'slowAES.decrypt' in content:
                # Try bypass methods
                bypass_methods = [
                    (url + '?i=1', {}),
                    (url + '?nocache=1', {}),
                    (url + f'?t={int(time.time())}', {}),
                    (url.replace('https://', 'http://'), {}),
                    (url, {'User-Agent': 'Googlebot/2.1 (+http://www.google.com/bot.html)'}),
                    (url, {'User-Agent': 'Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)'}),
                ]
                
                for bypass_url, headers in bypass_methods:
                    try:
                        response2 = await session.get(bypass_url, headers=headers)
                        content2 = response2.text
                        
                        if 'aes.js' not in content2 and 'slowAES.decrypt' not in content2:
                            return content2, str(response2.url)
                    except:
                        continue
                        
            return content, str(response.url)
            
        except Exception as e:
            print(f"Fetch error: {e}")
            return None, None
    
    async def try_different_access_methods(self, url: str):
        """Try different access methods"""
        parsed = urlparse(url)
        base_domain = parsed.netloc
        path = parsed.path
        
        # Common access patterns
        access_patterns = [
            f"https://{base_domain}{path}",
            f"http://{base_domain}{path}",
            f"https://{base_domain}/public_html{path}",
            f"https://{base_domain}/htdocs{path}",
            f"https://{base_domain}/www{path}",
        ]
        
        session = await self.get_session()
        
        for pattern_url in access_patterns:
            try:
                response = await session.get(pattern_url, timeout=10)
                if response.status_code == 200:
                    content = response.text
                    # Skip if it's just a bot trap
                    if self.is_valid_content(content):
                        return content, pattern_url
            except:
                continue
        
        return None, None
    
    def is_valid_content(self, content: str):
        """Check if content is valid (not a bot trap)"""
        if not content or len(content.strip()) < 50:
            return False
        
        # Check for common bot trap messages
        trap_messages = [
            'this is a trap for bots',
            'content loading',
            'please wait',
            'you are being redirected',
            'loading...',
        ]
        
        content_lower = content.lower()
        for trap in trap_messages:
            if trap in content_lower:
                return False
        
        # Check for basic HTML structure
        if '<html' not in content_lower and '<!doctype' not in content_lower:
            return False
        
        return True
    
    async def get_source_code(self, url: str):
        """Main function to get source code"""
        print(f"🔍 Extracting source from: {url}")
        
        try:
            # Method 1: Try protection bypass
            content1, url1 = await self.fetch_with_protection_bypass(url)
            
            if content1 and self.is_valid_content(content1):
                print("✅ Method 1 successful")
                return content1, url1
            
            # Method 2: Try different access methods
            content2, url2 = await self.try_different_access_methods(url)
            
            if content2:
                print("✅ Method 2 successful")
                return content2, url2
            
            # Method 3: Direct fetch as last resort
            session = await self.get_session()
            response = await session.get(url)
            content = response.text
            
            if self.is_valid_content(content):
                return content, str(response.url)
            
            return None, None
            
        except Exception as e:
            print(f"❌ Extraction error: {e}")
            return None, None
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.aclose()

# Create extractor instance
extractor = SourceExtractor()

@app.get("/")
async def root():
    """Root endpoint - redirect to API docs"""
    return JSONResponse({
        "message": "Web Source Extractor API",
        "endpoints": {
            "extract_source": "/api/protected?url=URL",
            "debug": "/api/debug?url=URL",
            "info": "/api/info"
        },
        "usage": "GET /api/protected?url=https://example.com",
        "example": "https://hs-websource-api.vercel.app/api/protected?url=https://zalim.kesug.com"
    })

@app.get("/api/protected")
async def extract_protected_source(url: str = Query(..., description="URL to extract source from")):
    """Extract source code from protected websites"""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    # Validate URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        # Get source code
        source_code, source_url = await extractor.get_source_code(url)
        
        if not source_code:
            raise HTTPException(
                status_code=404, 
                detail="Could not extract source code. The website might be heavily protected or inaccessible."
            )
        
        # Add metadata
        clean_html = f"""<!--
Extracted from: {url}
Source URL: {source_url}
Time: {datetime.now().isoformat()}
Powered by: Web Source Extractor API
-->

{source_code}
"""
        
        # Return as downloadable file
        filename = f"extracted-source-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
        
        return Response(
            content=clean_html,
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/html; charset=utf-8",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@app.get("/api/debug")
async def debug_url(url: str = Query(..., description="URL to debug")):
    """Debug endpoint to see what's being returned"""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                follow_redirects=True
            )
            
            content = response.text
            headers = dict(response.headers)
            
            # Check for protection patterns
            is_protected = 'aes.js' in content or 'slowAES.decrypt' in content
            is_bot_trap = any(phrase in content.lower() for phrase in [
                'this is a trap for bots',
                'content loading',
                'please wait'
            ])
            
            return JSONResponse({
                "url": str(response.url),
                "status_code": response.status_code,
                "content_length": len(content),
                "is_protected": is_protected,
                "is_bot_trap": is_bot_trap,
                "content_preview": content[:300] + "..." if len(content) > 300 else content,
                "headers": {k: v for k, v in headers.items() if k.lower() not in ['set-cookie', 'cookie']}
            })
            
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/info")
async def api_info():
    """Get API information"""
    return JSONResponse({
        "name": "Web Source Extractor API",
        "version": "1.0.0",
        "description": "Extract HTML source code from websites including protected ones",
        "author": "Haseeb Sahil",
        "endpoints": [
            {
                "path": "/api/protected",
                "method": "GET",
                "description": "Extract source code from URL",
                "parameters": {
                    "url": "Website URL to extract from (required)"
                },
                "example": "/api/protected?url=https://example.com"
            },
            {
                "path": "/api/debug",
                "method": "GET",
                "description": "Debug URL to see response",
                "example": "/api/debug?url=https://example.com"
            }
        ],
        "contact": {
            "telegram": "@HS_WebSource_Bot",
            "channel": "@hsmodzofc2"
        }
    })

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await extractor.close()

# For Vercel
async def handler(request):
    return app