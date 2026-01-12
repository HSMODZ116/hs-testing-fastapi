from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import httpx
import io
import asyncio
import re
import time
from urllib.parse import urljoin, urlparse
from datetime import datetime
import base64
import os

app = FastAPI(
    title="InfinityFree Direct Source Fetcher",
    description="Directly fetch original source from InfinityFree bypassing all protection",
    version="7.0.0"
)

# Configure templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

class DirectSourceFetcher:
    def __init__(self):
        self.session = None
        self.cookies = {}
        
    async def get_session(self):
        if not self.session:
            self.session = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            )
        return self.session
        
    async def fetch_with_manual_cookies(self, url: str):
        """Manual cookie handling for InfinityFree"""
        session = await self.get_session()
        
        # First, try to get the page normally
        print(f"Attempt 1: Direct fetch {url}")
        response = await session.get(url)
        
        # Check if we got the protection page
        content = response.text
        if 'aes.js' in content and 'slowAES.decrypt' in content:
            print("Got protection page, trying manual bypass...")
            
            # Extract the encrypted data
            pattern = r'toNumbers\("([a-f0-9]+)"\)'
            matches = re.findall(pattern, content)
            
            if len(matches) >= 3:
                # These are the AES parameters
                key_hex = matches[0]  # 32 chars = 16 bytes
                iv_hex = matches[1]   # 32 chars = 16 bytes  
                ciphertext_hex = matches[2]  # 32 chars = 16 bytes
                
                print(f"Found AES parameters: key={key_hex[:16]}..., iv={iv_hex[:16]}..., cipher={ciphertext_hex[:16]}...")
                
                # Try to simulate the cookie setting
                # InfinityFree uses this cookie format: __test=decrypted_value
                # We'll try to set a dummy cookie and retry
                
                # Add the cookie manually
                session.cookies.set('__test', 'bypassed_manual_cookie')
                
                # Wait a bit
                await asyncio.sleep(2)
                
                # Try accessing with ?i=1 parameter
                if '?' in url:
                    bypass_url = url + '&i=1'
                else:
                    bypass_url = url + '?i=1'
                
                print(f"Attempt 2: Accessing {bypass_url} with manual cookie")
                response2 = await session.get(bypass_url)
                
                # Also try without protection
                no_protection_url = url.replace('https://', 'http://')
                print(f"Attempt 3: Trying HTTP version {no_protection_url}")
                response3 = await session.get(no_protection_url)
                
                # Return the most promising response
                if response2.status_code == 200 and 'aes.js' not in response2.text:
                    return response2.text, str(response2.url)
                elif response3.status_code == 200 and 'aes.js' not in response3.text:
                    return response3.text, str(response3.url)
                
        return content, str(response.url)
    
    async def try_different_paths(self, url: str):
        """Try different common InfinityFree paths"""
        parsed = urlparse(url)
        base_domain = parsed.netloc
        path = parsed.path
        
        filename = path.split('/')[-1]
        base_path = '/'.join(path.split('/')[:-1]) if '/' in path else ''
        
        # Common InfinityFree file locations
        test_urls = [
            f"https://{base_domain}{path}",
            f"https://{base_domain}{path}?i=1",
            f"https://{base_domain}{path}?nocache=1",
            f"https://{base_domain}{path}?t={int(time.time())}",
            f"http://{base_domain}{path}",
            f"https://{base_domain}/public_html{path}",
            f"https://{base_domain}/htdocs{path}",
            f"https://{base_domain}/www{path}",
            f"https://{base_domain}/~{base_domain.split('.')[0]}{path}",
            f"https://{base_domain}/files{path}",
        ]
        
        session = await self.get_session()
        
        for test_url in test_urls:
            try:
                print(f"Trying path: {test_url}")
                response = await session.get(test_url, timeout=10)
                
                if response.status_code == 200:
                    content = response.text
                    # Check if it's the actual file and not protection
                    if not ('aes.js' in content and 'slowAES.decrypt' in content):
                        print(f"Found at: {test_url}")
                        return content, test_url
                        
                await asyncio.sleep(1)
            except Exception as e:
                continue
        
        return None, None
    
    async def extract_from_source_code(self, url: str):
        """Try to extract from page source or view-source"""
        try:
            # Try view-source
            view_source_url = f"view-source:{url}"
            
            # Actually, let's try with different headers
            session = await self.get_session()
            
            # Try with different Accept headers
            headers_list = [
                {'Accept': 'text/html'},
                {'Accept': '*/*'},
                {'Accept': 'text/plain'},
                {'User-Agent': 'Googlebot/2.1 (+http://www.google.com/bot.html)'},
                {'User-Agent': 'Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)'}
            ]
            
            for headers in headers_list:
                try:
                    response = await session.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        content = response.text
                        if '<!DOCTYPE html>' in content and 'aes.js' not in content:
                            return content, url
                except:
                    continue
            
            return None, None
        except Exception as e:
            print(f"Source extraction error: {e}")
            return None, None
    
    async def get_original_source(self, url: str):
        """Main function to get original source"""
        print(f"\n{'='*60}")
        print(f"Trying to extract original source from: {url}")
        print(f"{'='*60}")
        
        try:
            # Method 1: Try manual cookie bypass
            print("\n[Method 1] Manual cookie bypass...")
            content1, url1 = await self.fetch_with_manual_cookies(url)
            
            if content1 and 'aes.js' not in content1:
                print("✓ Success with manual cookie bypass!")
                return content1, url1
            
            # Method 2: Try different paths
            print("\n[Method 2] Trying different InfinityFree paths...")
            content2, url2 = await self.try_different_paths(url)
            
            if content2:
                print("✓ Found via path exploration!")
                return content2, url2
            
            # Method 3: Try to extract from source
            print("\n[Method 3] Trying source code extraction...")
            content3, url3 = await self.extract_from_source_code(url)
            
            if content3:
                print("✓ Extracted from source!")
                return content3, url3
            
            # Method 4: Last resort - try direct file access patterns
            print("\n[Method 4] Last resort - direct file patterns...")
            parsed = urlparse(url)
            
            # If we're getting protection page, the actual file might be at a different location
            # InfinityFree sometimes serves from /~username/ paths
            
            # Try common username patterns
            domain_parts = parsed.netloc.split('.')
            if len(domain_parts) >= 2:
                possible_user = domain_parts[0]  # e.g., 'hs-testing-tool' from 'hs-testing-tool.gt.tc'
                
                alt_urls = [
                    f"https://{parsed.netloc}/~{possible_user}{parsed.path}",
                    f"https://{parsed.netloc}/~{possible_user}/public_html{parsed.path}",
                    f"https://{parsed.netloc}/~{possible_user}/htdocs{parsed.path}",
                    f"https://{parsed.netloc}/~{possible_user}/www{parsed.path}",
                    f"https://{parsed.netloc}/{possible_user}{parsed.path}",
                ]
                
                session = await self.get_session()
                for alt_url in alt_urls:
                    try:
                        print(f"Trying: {alt_url}")
                        response = await session.get(alt_url, timeout=10)
                        if response.status_code == 200:
                            content = response.text
                            if 'aes.js' not in content:
                                print(f"✓ Found at alternative URL: {alt_url}")
                                return content, alt_url
                    except:
                        continue
            
            print("\n✗ All methods failed!")
            return None, None
            
        except Exception as e:
            print(f"\nError during extraction: {e}")
            return None, None
        
        finally:
            # Close session
            if self.session:
                await self.session.aclose()
                self.session = None

# Create fetcher instance
fetcher = DirectSourceFetcher()

@app.get("/")
async def home():
    return templates.TemplateResponse("index.html", {"request": {}})

@app.get("/api/recover")
async def recover_source(url: str = Query(..., description="InfinityFree URL to recover source from")):
    """Recover original source code from InfinityFree"""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        # Get original source
        source_code, source_url = await fetcher.get_original_source(url)
        
        if not source_code:
            raise HTTPException(status_code=404, detail="Could not recover source code. The file might be heavily protected or not accessible.")
        
        # Create a clean HTML file
        clean_html = f"""<!DOCTYPE html>
<!--
Recovered from: {url}
Source URL: {source_url}
Recovery Time: {datetime.now().isoformat()}
Original InfinityFree file recovered successfully
-->

{source_code}
"""
        
        # Return as downloadable file
        return Response(
            content=clean_html,
            media_type="text/html",
            headers={
                "Content-Disposition": "attachment; filename=recovered-original.html",
                "Content-Type": "text/html; charset=utf-8",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recovery failed: {str(e)}")

@app.get("/api/debug")
async def debug_url(url: str = Query(..., description="URL to debug")):
    """Debug endpoint to see what's being returned"""
    try:
        session = httpx.AsyncClient(timeout=30.0)
        response = await session.get(url, follow_redirects=True)
        
        content = response.text
        headers = dict(response.headers)
        
        # Check for InfinityFree patterns
        is_protected = 'aes.js' in content or 'slowAES.decrypt' in content
        
        return JSONResponse({
            "url": str(response.url),
            "status_code": response.status_code,
            "content_length": len(content),
            "is_infinityfree_protected": is_protected,
            "content_preview": content[:500] + "..." if len(content) > 500 else content,
            "headers": headers,
            "cookies": dict(response.cookies)
        })
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)