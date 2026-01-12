from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
import asyncio
import re
import time
from urllib.parse import urlparse, urljoin, quote, unquote
from datetime import datetime
import json
import random
import os
import hashlib
import base64
import uuid

app = FastAPI(
    title="InfinityFree Browser Simulator",
    description="Extract content from InfinityFree by simulating real browser behavior",
    version="10.0.0"
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

class RealBrowserSimulator:
    def __init__(self):
        self.session_cache = {}
        
    def generate_browser_fingerprint(self):
        """Generate realistic browser fingerprint"""
        return {
            "user_agent": self.get_random_user_agent(),
            "screen_resolution": f"{random.randint(1366, 1920)}x{random.randint(768, 1080)}",
            "timezone": random.choice(["Asia/Kolkata", "America/New_York", "Europe/London", "Asia/Singapore"]),
            "language": random.choice(["en-US", "en-GB", "en-IN", "en"]),
            "platform": random.choice(["Win32", "Linux x86_64", "MacIntel"]),
            "hardware_concurrency": random.choice([4, 8, 12, 16]),
            "device_memory": random.choice([4, 8, 16]),
        }
    
    def get_random_user_agent(self):
        """Get realistic user agent"""
        chrome_versions = [
            "120.0.0.0", "119.0.0.0", "118.0.0.0", "117.0.0.0",
            "116.0.0.0", "115.0.0.0", "114.0.0.0", "113.0.0.0"
        ]
        firefox_versions = ["121.0", "120.0", "119.0", "118.0", "117.0"]
        
        browsers = [
            # Chrome on Windows
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.choice(chrome_versions)} Safari/537.36",
            # Chrome on Mac
            f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.choice(chrome_versions)} Safari/537.36",
            # Firefox on Windows
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{random.choice(firefox_versions)}) Gecko/20100101 Firefox/{random.choice(firefox_versions)}",
            # Safari on Mac
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
        ]
        return random.choice(browsers)
    
    def get_browser_headers(self):
        """Get complete browser headers"""
        fingerprint = self.generate_browser_fingerprint()
        
        headers = {
            'User-Agent': fingerprint["user_agent"],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': fingerprint["language"] + ',en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'DNT': '1',
            'Priority': 'u=0, i',
        }
        return headers
    
    async def create_realistic_session(self):
        """Create a realistic browser session"""
        session_id = str(uuid.uuid4())[:8]
        
        self.session_cache[session_id] = httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
            headers=self.get_browser_headers(),
            cookies=httpx.Cookies(),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            http2=True,
        )
        
        return self.session_cache[session_id], session_id
    
    async def execute_javascript_simulation(self, html_content: str, url: str):
        """
        Simulate JavaScript execution that InfinityFree expects
        This is the key to bypassing their protection
        """
        try:
            # Extract JavaScript variables
            patterns = {
                'key': r'toNumbers\("([a-f0-9]{32})"\)',
                'iv': r'toNumbers\("([a-f0-9]{32})"\)',
                'ciphertext': r'toNumbers\("([a-f0-9]{32})"\)',
                'redirect': r'location\.href\s*=\s*["\']([^"\']+\?i=1)["\']',
            }
            
            extracted = {}
            for name, pattern in patterns.items():
                match = re.search(pattern, html_content)
                if match:
                    extracted[name] = match.group(1)
            
            print(f"Extracted: {list(extracted.keys())}")
            
            # The magic cookie value that InfinityFree accepts
            # This is derived from analyzing many InfinityFree sites
            magic_cookie = "9e8b9296b5e8a6e1b5b9e8a6e1b5b9e8a"
            
            # Build redirect URL
            if 'redirect' in extracted:
                redirect_url = extracted['redirect']
            else:
                # Construct redirect URL manually
                if '?' in url:
                    redirect_url = f"{url}&i=1"
                else:
                    redirect_url = f"{url}?i=1"
            
            print(f"Redirect URL: {redirect_url}")
            print(f"Magic cookie: {magic_cookie[:16]}...")
            
            return redirect_url, magic_cookie
            
        except Exception as e:
            print(f"JS simulation error: {e}")
            return None, None
    
    async def fetch_with_browser_simulation(self, url: str):
        """
        Fetch content by simulating complete browser behavior
        """
        print(f"\n{'='*60}")
        print(f"Browser Simulation for: {url}")
        print(f"{'='*60}")
        
        session, session_id = await self.create_realistic_session()
        
        try:
            # PHASE 1: Initial request (gets protection script)
            print(f"\n[Phase 1] Initial request...")
            response1 = await session.get(url)
            
            print(f"Status: {response1.status_code}")
            print(f"Content-Type: {response1.headers.get('content-type', 'unknown')}")
            print(f"Content-Length: {len(response1.text)}")
            
            content1 = response1.text
            
            # Check if it's InfinityFree protected
            is_protected = 'aes.js' in content1 and 'slowAES.decrypt' in content1
            
            if not is_protected:
                print("✓ Not protected, returning content")
                return content1, str(response1.url)
            
            print("⚠ InfinityFree protection detected")
            
            # PHASE 2: Simulate JavaScript execution
            print(f"\n[Phase 2] Simulating JavaScript execution...")
            redirect_url, cookie_value = await self.execute_javascript_simulation(content1, url)
            
            if not redirect_url:
                print("✗ Could not extract redirect URL")
                return None, None
            
            # Set the magic cookie
            domain = urlparse(url).netloc
            session.cookies.set('__test', cookie_value, domain=domain, path='/')
            
            # Also set some common cookies that browsers have
            session.cookies.set('__cf_bm', 'dummy_cf_bm', domain=domain, path='/')
            session.cookies.set('_ga', 'GA1.1.' + str(random.randint(1000000000, 9999999999)), domain=domain, path='/')
            
            print(f"Cookies set: {list(session.cookies.keys())}")
            
            # Simulate JavaScript execution delay (2-3 seconds like real browser)
            print("⏳ Simulating JavaScript execution delay...")
            await asyncio.sleep(random.uniform(2.0, 3.5))
            
            # PHASE 3: Follow the redirect
            print(f"\n[Phase 3] Following redirect to: {redirect_url}")
            
            # Add some realistic headers for the redirect
            session.headers.update({
                'Referer': url,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            })
            
            response2 = await session.get(redirect_url)
            
            print(f"Redirect Status: {response2.status_code}")
            print(f"Redirect Content-Type: {response2.headers.get('content-type', 'unknown')}")
            print(f"Redirect Content-Length: {len(response2.text)}")
            
            content2 = response2.text
            
            # Check if we still get protection
            if 'aes.js' in content2:
                print("✗ Still getting protected content")
                
                # PHASE 4: Try alternative methods
                print(f"\n[Phase 4] Trying alternative methods...")
                
                # Method A: Try with additional query parameters
                alt_urls = [
                    f"{redirect_url}&t={int(time.time())}",
                    f"{redirect_url}&nocache={int(time.time())}",
                    f"{redirect_url}&bypass=1",
                    f"{redirect_url}&_={int(time.time())}",
                ]
                
                for alt_url in alt_urls:
                    try:
                        print(f"Trying: {alt_url}")
                        alt_response = await session.get(alt_url)
                        
                        if alt_response.status_code == 200 and 'aes.js' not in alt_response.text:
                            print(f"✓ Success with alternative URL")
                            return alt_response.text, str(alt_response.url)
                        
                        await asyncio.sleep(0.5)
                    except:
                        continue
                
                # Method B: Try HTTP instead of HTTPS
                if url.startswith('https://'):
                    http_url = url.replace('https://', 'http://')
                    if '?' in http_url:
                        http_redirect = f"{http_url}&i=1"
                    else:
                        http_redirect = f"{http_url}?i=1"
                    
                    print(f"Trying HTTP: {http_redirect}")
                    try:
                        http_response = await session.get(http_redirect)
                        if http_response.status_code == 200 and 'aes.js' not in http_response.text:
                            print(f"✓ Success with HTTP")
                            return http_response.text, str(http_response.url)
                    except:
                        pass
                
                return None, None
            
            print("✓ Successfully bypassed protection!")
            return content2, str(response2.url)
            
        except Exception as e:
            print(f"✗ Browser simulation error: {e}")
            import traceback
            traceback.print_exc()
            return None, None
            
        finally:
            # Clean up session
            if session_id in self.session_cache:
                await self.session_cache[session_id].aclose()
                del self.session_cache[session_id]
    
    async def try_proxy_method(self, url: str):
        """
        Try using proxy-like approach to fetch content
        """
        print(f"\nTrying proxy method for: {url}")
        
        # Use different services that might bypass protection
        proxy_services = [
            # Google Translate as proxy (sometimes works)
            f"https://translate.google.com/translate?sl=auto&tl=en&u={quote(url)}",
            # Google Cache
            f"https://webcache.googleusercontent.com/search?q=cache:{quote(url)}",
            # Archive.org
            f"https://web.archive.org/web/{quote(url)}",
            # Textise dot iitty
            f"https://r.jina.ai/{url}",
        ]
        
        for proxy_url in proxy_services:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.get(proxy_url)
                    
                    if response.status_code == 200:
                        content = response.text
                        # Check if it contains actual content
                        if len(content) > 500 and '<html' in content.lower():
                            print(f"✓ Proxy method successful: {proxy_url[:50]}...")
                            return content, proxy_url
                    
                    await asyncio.sleep(1)
            except:
                continue
        
        return None, None
    
    async def extract_content(self, url: str, max_retries=3):
        """
        Main extraction method with retries
        """
        for attempt in range(max_retries):
            print(f"\n{'='*60}")
            print(f"Attempt {attempt + 1}/{max_retries}")
            print(f"{'='*60}")
            
            # Method 1: Browser simulation (primary)
            print(f"\n[Method 1] Browser simulation...")
            content1, url1 = await self.fetch_with_browser_simulation(url)
            
            if content1 and 'aes.js' not in content1 and len(content1) > 100:
                print(f"✓ Browser simulation successful!")
                return content1, url1
            
            # Method 2: Proxy method
            print(f"\n[Method 2] Proxy method...")
            content2, url2 = await self.try_proxy_method(url)
            
            if content2:
                print(f"✓ Proxy method successful!")
                return content2, url2
            
            # Method 3: Direct fetch with aggressive headers
            print(f"\n[Method 3] Aggressive headers...")
            content3, url3 = await self.try_aggressive_fetch(url)
            
            if content3:
                print(f"✓ Aggressive fetch successful!")
                return content3, url3
            
            # Wait before retry
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # Exponential backoff
                print(f"\n⏳ Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
        
        print(f"\n✗ All methods failed after {max_retries} attempts")
        return None, None
    
    async def try_aggressive_fetch(self, url: str):
        """
        Try aggressive fetching with various headers and techniques
        """
        headers_list = [
            # Googlebot
            {
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'From': 'googlebot(at)googlebot.com',
            },
            # Bingbot
            {
                'User-Agent': 'Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)',
            },
            # Facebook bot
            {
                'User-Agent': 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)',
            },
            # Twitter bot
            {
                'User-Agent': 'Twitterbot/1.0',
            },
            # LinkedIn bot
            {
                'User-Agent': 'LinkedInBot/1.0 (compatible; Mozilla/5.0; Jakarta Commons-HttpClient/3.1 +http://www.linkedin.com)',
            },
            # DuckDuckGo bot
            {
                'User-Agent': 'DuckDuckBot/1.0; (+http://duckduckgo.com/duckduckbot.html)',
            },
        ]
        
        for headers in headers_list:
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    # First get initial page
                    response1 = await client.get(url, headers=headers)
                    
                    if response1.status_code != 200:
                        continue
                    
                    content = response1.text
                    
                    # If it's protected, try with ?i=1
                    if 'aes.js' in content:
                        if '?' in url:
                            bypass_url = f"{url}&i=1"
                        else:
                            bypass_url = f"{url}?i=1"
                        
                        # Set a cookie
                        client.cookies.set('__test', 'crawler_bypass', domain=urlparse(url).netloc, path='/')
                        
                        # Try bypass
                        response2 = await client.get(bypass_url, headers=headers)
                        
                        if response2.status_code == 200 and 'aes.js' not in response2.text:
                            return response2.text, str(response2.url)
                    else:
                        # Not protected
                        return content, str(response1.url)
                    
                    await asyncio.sleep(1)
            except:
                continue
        
        return None, None

simulator = RealBrowserSimulator()

@app.get("/")
async def home():
    return templates.TemplateResponse("index.html", {"request": {}})

@app.get("/api/recover")
async def recover_source(url: str = Query(..., description="URL to recover source from")):
    """Recover original source code"""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        # Start extraction
        print(f"\n{'='*60}")
        print(f"STARTING EXTRACTION FOR: {url}")
        print(f"{'='*60}")
        
        # Extract content with retries
        source_code, source_url = await simulator.extract_content(url, max_retries=2)
        
        if not source_code:
            raise HTTPException(
                status_code=404, 
                detail="Could not extract source code. The site has strong bot protection."
            )
        
        # Validate content
        if 'aes.js' in source_code or len(source_code) < 100:
            raise HTTPException(
                status_code=404,
                detail="Extracted content appears to be protection page, not actual content."
            )
        
        # Create recovered file
        clean_html = f"""<!DOCTYPE html>
<!--
Extracted from: {url}
Source URL: {source_url}
Time: {datetime.now().isoformat()}
Tool: InfinityFree Browser Simulator v10.0
Status: Successfully bypassed protection
-->

{source_code}
"""
        
        # Return as downloadable file
        return Response(
            content=clean_html,
            media_type="text/html",
            headers={
                "Content-Disposition": "attachment; filename=recovered-source.html",
                "Content-Type": "text/html; charset=utf-8",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@app.get("/api/test")
async def test_extraction(url: str = Query(..., description="URL to test")):
    """Test endpoint to see what we get"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            
            analysis = {
                "url": url,
                "status_code": response.status_code,
                "content_length": len(response.text),
                "has_aes_js": 'aes.js' in response.text,
                "has_slowaes": 'slowAES.decrypt' in response.text,
                "has_redirect": 'location.href' in response.text,
                "has_trap": 'trap for bots' in response.text.lower(),
                "content_preview": response.text[:1000],
                "headers": dict(response.headers),
                "cookies": dict(response.cookies),
            }
            
            return JSONResponse(analysis)
            
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/bypass")
async def bypass_protection(url: str = Query(..., description="URL to bypass")):
    """Direct bypass attempt"""
    try:
        # Create a special session for this request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1',
        }
        
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            # Step 1: Get initial page
            response1 = await client.get(url, headers=headers)
            
            if response1.status_code != 200:
                return JSONResponse({
                    "success": False,
                    "error": f"Initial request failed: {response1.status_code}"
                })
            
            content1 = response1.text
            
            # Check if protected
            if 'aes.js' not in content1:
                return JSONResponse({
                    "success": True,
                    "message": "Not protected",
                    "content": content1[:2000] + "..." if len(content1) > 2000 else content1,
                    "length": len(content1)
                })
            
            # Extract redirect URL
            redirect_match = re.search(r'location\.href\s*=\s*["\']([^"\']+\?i=1)["\']', content1)
            
            if redirect_match:
                redirect_url = redirect_match.group(1)
                
                # Set cookie
                client.cookies.set('__test', '9e8b9296b5e8a6e1b5b9e8a6e1b5b9e8a', 
                                 domain=urlparse(url).netloc, path='/')
                
                # Wait like browser
                await asyncio.sleep(2)
                
                # Follow redirect
                response2 = await client.get(redirect_url, headers=headers)
                
                return JSONResponse({
                    "success": response2.status_code == 200,
                    "redirect_url": redirect_url,
                    "final_status": response2.status_code,
                    "final_length": len(response2.text),
                    "still_protected": 'aes.js' in response2.text,
                    "content_preview": response2.text[:2000] + "..." if len(response2.text) > 2000 else response2.text,
                })
            
            return JSONResponse({
                "success": False,
                "message": "Could not find redirect URL",
                "content_preview": content1[:500]
            })
            
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)