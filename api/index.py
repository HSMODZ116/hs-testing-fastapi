from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
import asyncio
import re
import time
from urllib.parse import urlparse
from datetime import datetime
import json
import random
import os

app = FastAPI(
    title="InfinityFree Direct Source Fetcher Pro",
    description="Advanced tool to extract original source from InfinityFree bypassing all protections",
    version="8.0.0"
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

class AdvancedSourceFetcher:
    def __init__(self):
        self.session = None
        
    async def get_session(self):
        if not self.session:
            self.session = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    'User-Agent': self.get_random_user_agent(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            )
        return self.session
    
    def get_random_user_agent(self):
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
            'Googlebot/2.1 (+http://www.google.com/bot.html)',
            'Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)'
        ]
        return random.choice(user_agents)
    
    async def analyze_protection(self, html_content: str):
        """Analyze what type of protection is being used"""
        protections = {
            'infinityfree_aes': 'aes.js' in html_content and 'slowAES.decrypt' in html_content,
            'trap_html': 'This is a trap for bots' in html_content or 'Content loading' in html_content,
            'js_redirect': 'setTimeout' in html_content and 'location.href' in html_content,
            'iframe_protection': 'iframe' in html_content.lower() and 'src' in html_content.lower(),
            'meta_refresh': 'meta http-equiv="refresh"' in html_content.lower(),
        }
        return protections
    
    async def extract_encrypted_data(self, html_content: str):
        """Extract AES encrypted data from InfinityFree protection"""
        patterns = {
            'toNumbers': r'toNumbers\("([a-f0-9]+)"\)',
            'hex_values': r'["\']([a-f0-9]{32,})["\']',
            'var_declarations': r'(?:var|let|const)\s+\w+\s*=\s*["\']([^"\']+)["\']',
            'script_content': r'<script[^>]*>([^<]+)</script>',
        }
        
        extracted = {}
        for name, pattern in patterns.items():
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            if matches:
                extracted[name] = matches
        
        return extracted
    
    async def bypass_js_protection(self, url: str):
        """Bypass JavaScript-based protection using various techniques"""
        session = await self.get_session()
        
        # Technique 1: Try with different query parameters
        query_params = [
            {'i': '1'},
            {'nocache': str(int(time.time()))},
            {'t': str(int(time.time()))},
            {'bypass': 'true'},
            {'view': 'source'},
            {'_': str(int(time.time()))}
        ]
        
        for params in query_params:
            try:
                response = await session.get(url, params=params, timeout=15)
                protections = await self.analyze_protection(response.text)
                if not protections['infinityfree_aes'] and not protections['trap_html']:
                    return response.text, str(response.url)
            except:
                continue
        
        # Technique 2: Try with different headers
        header_sets = [
            {'Referer': 'https://www.google.com/'},
            {'Referer': url},
            {'X-Requested-With': 'XMLHttpRequest'},
            {'Accept': 'application/json, text/javascript, */*; q=0.01'},
            {'Accept': 'text/plain'},
            {'X-Forwarded-For': f'192.168.{random.randint(1,255)}.{random.randint(1,255)}'}
        ]
        
        for headers in header_sets:
            try:
                current_headers = dict(session.headers)
                current_headers.update(headers)
                response = await session.get(url, headers=current_headers, timeout=15)
                protections = await self.analyze_protection(response.text)
                if not protections['trap_html']:
                    return response.text, str(response.url)
            except:
                continue
        
        return None, None
    
    async def try_direct_file_access(self, url: str):
        """Try direct file access patterns for InfinityFree"""
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path
        
        # Common InfinityFree directory structures
        common_dirs = ['', '/public_html', '/htdocs', '/www', '/files', '/web']
        
        # Try different protocol and path combinations
        access_patterns = []
        
        for protocol in ['https://', 'http://']:
            for dir_path in common_dirs:
                access_patterns.append(f"{protocol}{domain}{dir_path}{path}")
        
        # Try with username pattern (common in InfinityFree)
        if '.' in domain:
            username = domain.split('.')[0]
            for protocol in ['https://', 'http://']:
                access_patterns.append(f"{protocol}{domain}/~{username}{path}")
                access_patterns.append(f"{protocol}{domain}/{username}{path}")
        
        session = await self.get_session()
        
        for pattern_url in access_patterns:
            try:
                print(f"Trying direct access: {pattern_url}")
                response = await session.get(pattern_url, timeout=10)
                
                if response.status_code == 200:
                    content = response.text
                    protections = await self.analyze_protection(content)
                    
                    if not protections['trap_html'] and len(content) > 100:
                        print(f"✓ Found via direct access: {pattern_url}")
                        return content, pattern_url
                
                await asyncio.sleep(0.5)
            except Exception as e:
                continue
        
        return None, None
    
    async def simulate_browser_behavior(self, url: str):
        """Simulate actual browser behavior to bypass protections"""
        session = await self.get_session()
        
        # Step 1: First request to get cookies
        try:
            response1 = await session.get(url, timeout=15)
            
            # Step 2: Wait as if it's a real browser
            await asyncio.sleep(random.uniform(1, 3))
            
            # Step 3: Try again with cookies from first request
            response2 = await session.get(url, timeout=15)
            
            # Step 4: Check if we got different content
            if response1.text != response2.text:
                protections2 = await self.analyze_protection(response2.text)
                if not protections2['trap_html']:
                    return response2.text, str(response2.url)
            
            # Step 5: Try POST request (sometimes works)
            try:
                response3 = await session.post(url, data={'get_source': 'true'}, timeout=15)
                protections3 = await self.analyze_protection(response3.text)
                if not protections3['trap_html']:
                    return response3.text, str(response3.url)
            except:
                pass
                
        except Exception as e:
            print(f"Browser simulation error: {e}")
        
        return None, None
    
    async def extract_real_content(self, url: str):
        """Main method to extract real content using multiple techniques"""
        print(f"\n{'='*60}")
        print(f"Advanced Extraction from: {url}")
        print(f"{'='*60}")
        
        results = []
        
        # Method 1: Direct fetch with analysis
        print("\n[Method 1] Direct fetch with protection analysis...")
        session = await self.get_session()
        try:
            response = await session.get(url, timeout=15)
            protections = await self.analyze_protection(response.text)
            print(f"Protection analysis: {protections}")
            
            if not protections['trap_html'] and len(response.text) > 500:
                print("✓ Direct fetch successful!")
                return response.text, str(response.url)
        except Exception as e:
            print(f"Direct fetch error: {e}")
        
        # Method 2: JS Protection bypass
        print("\n[Method 2] JavaScript protection bypass...")
        content2, url2 = await self.bypass_js_protection(url)
        if content2:
            print("✓ JS bypass successful!")
            return content2, url2
        
        # Method 3: Direct file access
        print("\n[Method 3] Direct file access patterns...")
        content3, url3 = await self.try_direct_file_access(url)
        if content3:
            print("✓ Direct access successful!")
            return content3, url3
        
        # Method 4: Browser simulation
        print("\n[Method 4] Browser behavior simulation...")
        content4, url4 = await self.simulate_browser_behavior(url)
        if content4:
            print("✓ Browser simulation successful!")
            return content4, url4
        
        # Method 5: Try view-source
        print("\n[Method 5] View-source method...")
        try:
            view_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/plain'
            }
            response5 = await session.get(url, headers=view_headers, timeout=15)
            if len(response5.text) > 300:
                print("✓ View-source successful!")
                return response5.text, str(response5.url)
        except:
            pass
        
        print("\n✗ All extraction methods failed!")
        return None, None

fetcher = AdvancedSourceFetcher()

@app.get("/")
async def home():
    return templates.TemplateResponse("index.html", {"request": {}})

@app.get("/api/recover")
async def recover_source(url: str = Query(..., description="URL to recover source from")):
    """Recover original source code"""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        # Get original source using advanced methods
        source_code, source_url = await fetcher.extract_real_content(url)
        
        if not source_code:
            # Try one more time with different approach
            session = httpx.AsyncClient(timeout=30)
            try:
                response = await session.get(url)
                protections = await fetcher.analyze_protection(response.text)
                
                if protections['trap_html']:
                    raise HTTPException(
                        status_code=404, 
                        detail="Content is protected with anti-bot trap. Try using /api/protected endpoint."
                    )
                
                source_code = response.text
                source_url = str(response.url)
            finally:
                await session.aclose()
        
        if not source_code:
            raise HTTPException(
                status_code=404, 
                detail="Could not extract source code. The content might be heavily protected."
            )
        
        # Create recovered file
        clean_html = f"""<!DOCTYPE html>
<!--
Extracted from: {url}
Source URL: {source_url}
Time: {datetime.now().isoformat()}
Powered by: InfinityFree Source Recovery Tool
-->
{source_code}
"""
        
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
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@app.get("/api/protected")
async def extract_protected_content(url: str = Query(..., description="Protected URL to extract from")):
    """Special endpoint for heavily protected content"""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        # Multiple attempts with different strategies
        strategies = [
            ("Direct with referer", {"Referer": "https://www.google.com/"}),
            ("AJAX request", {"X-Requested-With": "XMLHttpRequest"}),
            ("Mobile user agent", {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"}),
            ("Crawler", {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}),
        ]
        
        session = httpx.AsyncClient(timeout=30)
        results = []
        
        for strategy_name, headers in strategies:
            try:
                response = await session.get(url, headers=headers)
                protections = await fetcher.analyze_protection(response.text)
                
                results.append({
                    "strategy": strategy_name,
                    "url": str(response.url),
                    "status": response.status_code,
                    "length": len(response.text),
                    "protections": protections,
                    "preview": response.text[:200] if response.text else ""
                })
                
                # If we got non-trap content, use it
                if not protections['trap_html'] and len(response.text) > 300:
                    await session.aclose()
                    
                    return JSONResponse({
                        "success": True,
                        "strategy_used": strategy_name,
                        "content_length": len(response.text),
                        "source_url": str(response.url),
                        "content": response.text
                    })
                    
            except Exception as e:
                results.append({
                    "strategy": strategy_name,
                    "error": str(e)
                })
        
        await session.aclose()
        
        # Return analysis if all failed
        return JSONResponse({
            "success": False,
            "message": "All extraction strategies failed",
            "target_url": url,
            "strategies_tried": results,
            "suggestion": "Content is heavily protected. Try accessing through a different method."
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Protected extraction failed: {str(e)}")

@app.get("/api/debug")
async def debug_url(url: str = Query(..., description="URL to debug")):
    """Debug endpoint with detailed analysis"""
    try:
        session = httpx.AsyncClient(timeout=30.0)
        response = await session.get(url, follow_redirects=True)
        
        content = response.text
        protections = await fetcher.analyze_protection(content)
        extracted_data = await fetcher.extract_encrypted_data(content)
        
        analysis = {
            "url": str(response.url),
            "final_url": str(response.url),
            "status_code": response.status_code,
            "content_length": len(content),
            "protection_analysis": protections,
            "has_trap": protections['trap_html'],
            "has_aes": protections['infinityfree_aes'],
            "extracted_patterns": {k: len(v) for k, v in extracted_data.items()},
            "headers": dict(response.headers),
            "cookies": dict(response.cookies),
            "content_preview": content[:1000] if len(content) > 1000 else content,
            "recommendation": "Use /api/protected endpoint" if protections['trap_html'] else "Use /api/recover endpoint"
        }
        
        await session.aclose()
        return JSONResponse(analysis)
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)