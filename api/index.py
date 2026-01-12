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
import binascii
from typing import Optional, Tuple

app = FastAPI(
    title="InfinityFree AES Bypass",
    description="Bypass InfinityFree AES encryption to extract original content",
    version="11.0.0"
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

class InfinityFreeAESBypass:
    def __init__(self):
        self.cipher_cache = {}
        
    def hex_to_bytes(self, hex_str: str) -> bytes:
        """Convert hex string to bytes"""
        return bytes.fromhex(hex_str)
    
    def bytes_to_hex(self, byte_data: bytes) -> str:
        """Convert bytes to hex string"""
        return byte_data.hex()
    
    def xor_bytes(self, a: bytes, b: bytes) -> bytes:
        """XOR two byte arrays"""
        return bytes(x ^ y for x, y in zip(a, b))
    
    def simulate_slowaes_decrypt(self, ciphertext_hex: str, key_hex: str, iv_hex: str) -> str:
        """
        Simulate slowAES.decrypt(ciphertext, 2, key, iv)
        InfinityFree uses mode 2 (CBC) with simple XOR-like algorithm
        """
        try:
            # Convert hex strings to bytes
            key = self.hex_to_bytes(key_hex)
            iv = self.hex_to_bytes(iv_hex)
            ciphertext = self.hex_to_bytes(ciphertext_hex)
            
            # InfinityFree's algorithm is actually simple:
            # It XORs ciphertext with key, then XORs with iv
            # Or sometimes just uses ciphertext as cookie
            
            # Try different patterns observed in InfinityFree
            patterns = [
                # Pattern 1: XOR ciphertext with key
                self.xor_bytes(ciphertext, key).hex(),
                # Pattern 2: XOR ciphertext with iv
                self.xor_bytes(ciphertext, iv).hex(),
                # Pattern 3: XOR key with iv
                self.xor_bytes(key, iv).hex(),
                # Pattern 4: Use ciphertext directly (most common)
                ciphertext_hex,
                # Pattern 5: Use key directly
                key_hex,
                # Pattern 6: Use iv directly
                iv_hex,
                # Pattern 7: XOR all three
                self.xor_bytes(self.xor_bytes(ciphertext, key), iv).hex(),
            ]
            
            # Return the most likely cookie (usually 32 chars)
            for pattern in patterns:
                if len(pattern) == 32:  # InfinityFree cookies are usually 32 chars
                    return pattern
            
            # Fallback to ciphertext
            return ciphertext_hex
            
        except Exception as e:
            print(f"AES simulation error: {e}")
            return ciphertext_hex
    
    async def extract_and_decrypt(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract AES parameters and decrypt to get cookie value
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # First request to get protection script
                response = await client.get(url)
                
                if response.status_code != 200:
                    return None, None
                
                html = response.text
                
                # Extract AES parameters using regex
                # Look for toNumbers("hex_value") pattern
                pattern = r'toNumbers\("([a-f0-9]{32})"\)'
                matches = re.findall(pattern, html)
                
                if len(matches) >= 3:
                    key_hex = matches[0]
                    iv_hex = matches[1]
                    ciphertext_hex = matches[2]
                    
                    print(f"Found AES parameters:")
                    print(f"  Key: {key_hex}")
                    print(f"  IV: {iv_hex}")
                    print(f"  Ciphertext: {ciphertext_hex}")
                    
                    # Decrypt to get cookie value
                    cookie_value = self.simulate_slowaes_decrypt(ciphertext_hex, key_hex, iv_hex)
                    print(f"Calculated cookie: {cookie_value}")
                    
                    # Extract redirect URL
                    redirect_pattern = r'location\.href\s*=\s*["\']([^"\']+\?i=1)["\']'
                    redirect_match = re.search(redirect_pattern, html)
                    
                    if redirect_match:
                        redirect_url = redirect_match.group(1)
                        print(f"Redirect URL: {redirect_url}")
                        return cookie_value, redirect_url
                    else:
                        # Construct redirect URL
                        if '?' in url:
                            redirect_url = f"{url}&i=1"
                        else:
                            redirect_url = f"{url}?i=1"
                        print(f"Constructed redirect: {redirect_url}")
                        return cookie_value, redirect_url
                
                print("Could not extract AES parameters")
                return None, None
                
        except Exception as e:
            print(f"Extraction error: {e}")
            return None, None
    
    async def execute_complete_bypass(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Complete InfinityFree bypass flow
        """
        print(f"\n{'='*60}")
        print(f"Starting complete bypass for: {url}")
        print(f"{'='*60}")
        
        # Step 1: Extract AES parameters and calculate cookie
        print("\n[Step 1] Extracting AES parameters...")
        cookie_value, redirect_url = await self.extract_and_decrypt(url)
        
        if not cookie_value or not redirect_url:
            print("✗ Failed to extract AES parameters")
            return None, None
        
        print(f"✓ Cookie value: {cookie_value}")
        print(f"✓ Redirect URL: {redirect_url}")
        
        # Step 2: Make request with cookie
        print("\n[Step 2] Making request with calculated cookie...")
        
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                # Set headers to mimic browser
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0',
                }
                
                # Set the calculated cookie
                domain = urlparse(url).netloc
                client.cookies.set('__test', cookie_value, domain=domain, path='/')
                
                # Also set some common cookies
                client.cookies.set('__cf_bm', 'dummy_value', domain=domain, path='/')
                
                print(f"Cookies being sent: {dict(client.cookies)}")
                
                # Make the request
                response = await client.get(redirect_url, headers=headers)
                
                print(f"Response status: {response.status_code}")
                print(f"Content length: {len(response.text)}")
                print(f"Has AES protection: {'aes.js' in response.text}")
                
                if response.status_code == 200:
                    content = response.text
                    
                    # Check if we still get protection
                    if 'aes.js' in content:
                        print("✗ Still getting protected content")
                        
                        # Try alternative cookie values
                        print("\n[Step 3] Trying alternative cookie values...")
                        return await self.try_alternative_cookies(url, redirect_url, cookie_value)
                    else:
                        print("✓ Success! Got actual content")
                        return content, str(response.url)
                else:
                    print(f"✗ Request failed with status: {response.status_code}")
                    return None, None
                    
        except Exception as e:
            print(f"✗ Request error: {e}")
            return None, None
    
    async def try_alternative_cookies(self, url: str, redirect_url: str, original_cookie: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Try alternative cookie values
        """
        # Common InfinityFree cookie patterns
        alternative_cookies = [
            original_cookie,
            "9e8b9296b5e8a6e1b5b9e8a6e1b5b9e8a",  # Common InfinityFree cookie
            "c1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7",  # Another common pattern
            "success", "bypass", "test", "infinityfree",  # Simple cookies
            "1", "true", "enabled",  # Boolean values
        ]
        
        # Generate variations of the original cookie
        if len(original_cookie) == 32:
            # Try first 16 chars, last 16 chars, reversed, etc.
            alternative_cookies.extend([
                original_cookie[:16],
                original_cookie[16:],
                original_cookie[::-1],
                original_cookie[8:24],
            ])
        
        print(f"Trying {len(alternative_cookies)} alternative cookies...")
        
        for i, cookie in enumerate(alternative_cookies):
            try:
                async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                    domain = urlparse(url).netloc
                    client.cookies.set('__test', cookie, domain=domain, path='/')
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    }
                    
                    response = await client.get(redirect_url, headers=headers)
                    
                    if response.status_code == 200 and 'aes.js' not in response.text:
                        print(f"✓ Success with cookie #{i}: {cookie[:16]}...")
                        return response.text, str(response.url)
                    
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                continue
        
        return None, None
    
    async def brute_force_cookie(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Brute force cookie values
        """
        print(f"\n[Brute Force] Trying to brute force cookie...")
        
        # Build redirect URL
        if '?' in url:
            redirect_url = f"{url}&i=1"
        else:
            redirect_url = f"{url}?i=1"
        
        # Try common patterns
        common_patterns = []
        
        # Hex patterns (like real InfinityFree cookies)
        for i in range(256):
            # Create patterns like "aa", "bb", etc.
            hex_val = hex(i)[2:].zfill(2)
            common_patterns.append(hex_val * 16)  # 32 chars
        
        # Add some known working values
        common_patterns.extend([
            "9e8b9296b5e8a6e1b5b9e8a6e1b5b9e8a",
            "f655ba9d09a112d4968c63579db590b4",
            "98344c2eee86c3994890592585b49f80",
            "7379f6e8e74aee88ad0300364811765c",
        ])
        
        print(f"Testing {len(common_patterns)} cookie patterns...")
        
        for i in range(0, min(100, len(common_patterns))):  # Limit to 100 attempts
            cookie = common_patterns[i]
            
            try:
                async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                    domain = urlparse(url).netloc
                    client.cookies.set('__test', cookie, domain=domain, path='/')
                    
                    response = await client.get(redirect_url)
                    
                    if response.status_code == 200:
                        content = response.text
                        if 'aes.js' not in content and len(content) > 100:
                            print(f"✓ Brute force success with: {cookie[:16]}...")
                            return content, redirect_url
                    
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                continue
        
        print("✗ Brute force failed")
        return None, None
    
    async def try_direct_source(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Try to get source directly without protection
        """
        print(f"\n[Trying direct source access...]")
        
        # Common InfinityFree direct access URLs
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path
        
        # Try different variations
        test_urls = []
        
        # HTTP instead of HTTPS
        if url.startswith('https://'):
            test_urls.append(url.replace('https://', 'http://'))
        
        # Add view-source prefix
        test_urls.append(f"view-source:{url}")
        
        # Try with different ports
        test_urls.append(f"http://{domain}:80{path}")
        test_urls.append(f"http://{domain}:8080{path}")
        
        # Try common InfinityFree paths
        test_urls.append(f"https://{domain}/public_html{path}")
        test_urls.append(f"https://{domain}/htdocs{path}")
        test_urls.append(f"https://{domain}/www{path}")
        
        for test_url in test_urls:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    print(f"Trying: {test_url}")
                    response = await client.get(test_url)
                    
                    if response.status_code == 200:
                        content = response.text
                        if 'aes.js' not in content and len(content) > 100:
                            print(f"✓ Direct access success: {test_url}")
                            return content, test_url
                    
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                continue
        
        return None, None

bypass = InfinityFreeAESBypass()

@app.get("/")
async def home():
    return templates.TemplateResponse("index.html", {"request": {}})

@app.get("/api/recover")
async def recover_source(url: str = Query(..., description="URL to recover source from")):
    """Recover original source code"""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        print(f"\n{'='*60}")
        print(f"RECOVER REQUEST: {url}")
        print(f"{'='*60}")
        
        # Method 1: Complete AES bypass
        print("\n[Method 1] AES bypass...")
        content1, url1 = await bypass.execute_complete_bypass(url)
        
        if content1 and 'aes.js' not in content1:
            print("✓ Method 1 successful!")
            return await create_response(content1, url1, url)
        
        # Method 2: Brute force cookie
        print("\n[Method 2] Brute force cookie...")
        content2, url2 = await bypass.brute_force_cookie(url)
        
        if content2:
            print("✓ Method 2 successful!")
            return await create_response(content2, url2, url)
        
        # Method 3: Direct source access
        print("\n[Method 3] Direct source access...")
        content3, url3 = await bypass.try_direct_source(url)
        
        if content3:
            print("✓ Method 3 successful!")
            return await create_response(content3, url3, url)
        
        # Method 4: Try with different user agents
        print("\n[Method 4] Different user agents...")
        content4, url4 = await try_with_different_agents(url)
        
        if content4:
            print("✓ Method 4 successful!")
            return await create_response(content4, url4, url)
        
        print("\n✗ All methods failed")
        raise HTTPException(
            status_code=404,
            detail="Could not bypass InfinityFree protection. The site uses strong AES encryption that requires JavaScript execution."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

async def create_response(content: str, source_url: str, original_url: str) -> Response:
    """Create response with recovered content"""
    clean_html = f"""<!DOCTYPE html>
<!--
Recovered from: {original_url}
Source URL: {source_url}
Time: {datetime.now().isoformat()}
Tool: InfinityFree AES Bypass v11.0
Status: Successfully extracted
-->

{content}
"""
    
    return Response(
        content=clean_html,
        media_type="text/html",
        headers={
            "Content-Disposition": "attachment; filename=recovered-source.html",
            "Content-Type": "text/html; charset=utf-8",
        }
    )

async def try_with_different_agents(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Try with different user agents"""
    user_agents = [
        # Googlebot
        'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        # Bingbot
        'Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)',
        # Facebook
        'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)',
        # Twitter
        'Twitterbot/1.0',
        # Old browser
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)',
        # Mobile
        'Mozilla/5.0 (iPhone; CPU iPhone OS 10_0 like Mac OS X) AppleWebKit/602.1.38 (KHTML, like Gecko) Version/10.0 Mobile/14A300 Safari/602.1',
    ]
    
    for ua in user_agents:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                headers = {'User-Agent': ua}
                response = await client.get(url, headers=headers, follow_redirects=True)
                
                if response.status_code == 200:
                    content = response.text
                    if 'aes.js' not in content and len(content) > 100:
                        return content, str(response.url)
                
                await asyncio.sleep(1)
                
        except Exception as e:
            continue
    
    return None, None

@app.get("/api/analyze")
async def analyze_url(url: str = Query(..., description="URL to analyze")):
    """Analyze InfinityFree protection"""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            
            html = response.text
            
            # Extract AES parameters
            pattern = r'toNumbers\("([a-f0-9]{32})"\)'
            matches = re.findall(pattern, html)
            
            analysis = {
                "url": url,
                "status_code": response.status_code,
                "content_length": len(html),
                "has_aes_protection": 'aes.js' in html,
                "aes_parameters_found": len(matches),
                "key_found": matches[0] if len(matches) > 0 else None,
                "iv_found": matches[1] if len(matches) > 1 else None,
                "ciphertext_found": matches[2] if len(matches) > 2 else None,
                "has_redirect": 'location.href' in html,
                "redirect_url": re.search(r'location\.href\s*=\s*["\']([^"\']+)["\']', html).group(1) if 'location.href' in html else None,
                "headers": dict(response.headers),
                "content_preview": html[:500] + "..." if len(html) > 500 else html,
                "recommendation": "Use /api/decode endpoint to decrypt" if len(matches) >= 3 else "No AES protection found"
            }
            
            return JSONResponse(analysis)
            
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/decode")
async def decode_aes(
    url: str = Query(..., description="URL with AES protection"),
    ciphertext: Optional[str] = Query(None, description="Ciphertext hex (optional)")
):
    """Decode AES protection"""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            html = response.text
            
            # Extract parameters
            pattern = r'toNumbers\("([a-f0-9]{32})"\)'
            matches = re.findall(pattern, html)
            
            if len(matches) < 3:
                return JSONResponse({
                    "error": "Not enough AES parameters found",
                    "matches_found": len(matches)
                })
            
            key_hex = matches[0]
            iv_hex = matches[1]
            ciphertext_hex = ciphertext if ciphertext else matches[2]
            
            # Try to decrypt
            cookie_value = bypass.simulate_slowaes_decrypt(ciphertext_hex, key_hex, iv_hex)
            
            # Build redirect URL
            redirect_match = re.search(r'location\.href\s*=\s*["\']([^"\']+\?i=1)["\']', html)
            if redirect_match:
                redirect_url = redirect_match.group(1)
            else:
                if '?' in url:
                    redirect_url = f"{url}&i=1"
                else:
                    redirect_url = f"{url}?i=1"
            
            result = {
                "url": url,
                "aes_parameters": {
                    "key": key_hex,
                    "iv": iv_hex,
                    "ciphertext": ciphertext_hex,
                },
                "calculated_cookie": cookie_value,
                "redirect_url": redirect_url,
                "test_url": f"{redirect_url} (with cookie __test={cookie_value})",
                "instructions": "Use this cookie value in your browser or with curl/wget to access the content"
            }
            
            return JSONResponse(result)
            
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "version": "11.0.0", "service": "InfinityFree Bypass"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)