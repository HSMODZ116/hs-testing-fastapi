from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response, JSONResponse, HTMLResponse
import httpx
import asyncio
import re
import time
from urllib.parse import urljoin, urlparse
from datetime import datetime
from playwright.async_api import async_playwright
import os

app = FastAPI(
    title="Web Source Extractor Pro",
    description="Extract full source code from any website including JavaScript-rendered content",
    version="10.0.0"
)

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
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            )
        return self.browser
        
    async def extract_with_playwright(self, url: str):
        """Extract content using headless browser for JS sites"""
        print(f"🔍 Using Playwright to extract: {url}")
        
        browser = await self.init_browser()
        
        try:
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                java_script_enabled=True,
                bypass_csp=False,
                ignore_https_errors=True,
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                }
            )
            
            page = await context.new_page()
            
            print("🌐 Loading page...")
            await page.goto(url, wait_until='networkidle', timeout=60000)
            
            # Wait for JavaScript to execute
            await asyncio.sleep(2)
            
            # Scroll to trigger lazy loading
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)
            
            # Get fully rendered HTML
            html = await page.content()
            title = await page.title()
            final_url = page.url
            
            await context.close()
            
            print(f"✅ Extracted: {title}")
            return html, final_url
            
        except Exception as e:
            print(f"❌ Playwright error: {e}")
            return None, None
    
    async def extract_with_httpx(self, url: str):
        """Try traditional HTTP extraction for static sites"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return response.text, str(response.url)
                    
        except Exception as e:
            print(f"❌ HTTPX error: {e}")
            
        return None, None
    
    async def bypass_infinityfree(self, url: str):
        """Special bypass for InfinityFree protection"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }
            
            # Try different InfinityFree bypass methods
            urls_to_try = [
                url,
                url.replace('https://', 'http://'),
                url + '?i=1',
                url + '?nocache=1',
                url + f'?t={int(time.time())}',
            ]
            
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                for test_url in urls_to_try:
                    try:
                        print(f"🔄 Trying: {test_url}")
                        response = await client.get(test_url, headers=headers)
                        
                        if response.status_code == 200:
                            content = response.text
                            # Check if it's protected
                            if 'aes.js' not in content and 'slowAES.decrypt' not in content:
                                print(f"✅ Bypassed protection!")
                                return content, test_url
                    except:
                        continue
                        
        except Exception as e:
            print(f"❌ InfinityFree bypass error: {e}")
            
        return None, None
    
    async def get_full_source(self, url: str):
        """Main extraction method with multiple strategies"""
        print(f"\n{'='*60}")
        print(f"🎯 Extracting from: {url}")
        print(f"{'='*60}")
        
        # Check if it's InfinityFree
        if 'infinityfree' in url.lower() or '.ifastnet' in url or '.epizy' in url:
            print("\n[Method 1] InfinityFree bypass...")
            content, source_url = await self.bypass_infinityfree(url)
            if content:
                return content, source_url
        
        # Try traditional HTTP first (fastest)
        print("\n[Method 2] Traditional HTTP extraction...")
        content, source_url = await self.extract_with_httpx(url)
        
        if content and self.is_valid_content(content):
            print("✅ Success with HTTP!")
            return content, source_url
        
        # Use Playwright for JavaScript sites
        print("\n[Method 3] Headless browser extraction...")
        content, source_url = await self.extract_with_playwright(url)
        
        if content:
            print("✅ Success with Playwright!")
            return content, source_url
        
        print("\n❌ All extraction methods failed!")
        return None, None
    
    def is_valid_content(self, html: str):
        """Check if HTML contains actual content"""
        if not html or len(html.strip()) < 100:
            return False
        
        trap_indicators = [
            'This is a trap for bots',
            'Content loading...',
            'Please wait...',
            'Loading...',
            '<body></body>',
            '<body> </body>',
        ]
        
        for indicator in trap_indicators:
            if indicator.lower() in html.lower():
                return False
        
        return True
    
    async def close(self):
        """Cleanup resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

# Create extractor instance
extractor = WebSourceExtractor()

@app.get("/")
async def home():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Web Source Extractor Pro</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            body {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            
            .container {
                background: rgba(255, 255, 255, 0.95);
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                width: 100%;
                max-width: 900px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            
            .header {
                text-align: center;
                margin-bottom: 40px;
            }
            
            h1 {
                color: #333;
                font-size: 3em;
                margin-bottom: 10px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .tagline {
                color: #666;
                font-size: 1.2em;
                margin-bottom: 30px;
            }
            
            .input-group {
                margin-bottom: 30px;
            }
            
            input[type="url"] {
                width: 100%;
                padding: 18px 25px;
                font-size: 18px;
                border: 2px solid #ddd;
                border-radius: 12px;
                transition: all 0.3s;
                background: white;
            }
            
            input[type="url"]:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
            }
            
            .extract-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 18px 40px;
                font-size: 18px;
                font-weight: bold;
                border-radius: 12px;
                cursor: pointer;
                width: 100%;
                transition: all 0.3s;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }
            
            .extract-btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }
            
            .extract-btn:active {
                transform: translateY(-1px);
            }
            
            .result {
                margin-top: 30px;
                padding: 20px;
                border-radius: 12px;
                display: none;
                animation: slideDown 0.3s ease;
            }
            
            @keyframes slideDown {
                from {
                    opacity: 0;
                    transform: translateY(-10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .success {
                background: #e8f5e9;
                border: 2px solid #4CAF50;
                color: #2e7d32;
            }
            
            .error {
                background: #ffebee;
                border: 2px solid #f44336;
                color: #c62828;
            }
            
            .loading {
                background: #e3f2fd;
                border: 2px solid #2196f3;
                color: #1565c0;
            }
            
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-top: 40px;
            }
            
            .feature {
                background: white;
                padding: 25px;
                border-radius: 12px;
                text-align: center;
                box-shadow: 0 5px 15px rgba(0,0,0,0.05);
                border: 1px solid #eee;
                transition: transform 0.3s;
            }
            
            .feature:hover {
                transform: translateY(-5px);
            }
            
            .feature-icon {
                font-size: 2.5em;
                margin-bottom: 15px;
            }
            
            .feature h3 {
                color: #333;
                margin-bottom: 10px;
            }
            
            .feature p {
                color: #666;
                font-size: 0.95em;
                line-height: 1.5;
            }
            
            .api-info {
                background: #f8f9fa;
                padding: 25px;
                border-radius: 12px;
                margin-top: 40px;
                border: 1px solid #dee2e6;
            }
            
            .api-info h3 {
                color: #333;
                margin-bottom: 15px;
            }
            
            code {
                background: #333;
                color: #fff;
                padding: 12px 20px;
                border-radius: 8px;
                display: block;
                margin: 10px 0;
                font-family: 'Courier New', monospace;
                overflow-x: auto;
            }
            
            .test-urls {
                display: flex;
                gap: 10px;
                margin-top: 20px;
                flex-wrap: wrap;
            }
            
            .test-btn {
                background: #e3f2fd;
                color: #1565c0;
                border: 1px solid #bbdefb;
                padding: 10px 20px;
                border-radius: 20px;
                cursor: pointer;
                transition: all 0.3s;
                font-size: 14px;
            }
            
            .test-btn:hover {
                background: #bbdefb;
                transform: translateY(-2px);
            }
            
            .footer {
                text-align: center;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                color: #666;
                font-size: 0.9em;
            }
            
            @media (max-width: 768px) {
                .container {
                    padding: 25px;
                }
                
                h1 {
                    font-size: 2.2em;
                }
                
                input[type="url"], .extract-btn {
                    padding: 15px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌐 Web Source Extractor Pro</h1>
                <p class="tagline">Extract full HTML source code from any website, including JavaScript-rendered content</p>
            </div>
            
            <div class="input-group">
                <input type="url" id="urlInput" 
                       placeholder="Enter website URL (e.g., https://example.com)" 
                       value="https://zalim.kesug.com">
                <div class="test-urls">
                    <button class="test-btn" onclick="setUrl('https://zalim.kesug.com')">Test Site 1</button>
                    <button class="test-btn" onclick="setUrl('https://react.dev')">React</button>
                    <button class="test-btn" onclick="setUrl('https://vuejs.org')">Vue.js</button>
                    <button class="test-btn" onclick="setUrl('https://infinityfree.net')">InfinityFree</button>
                </div>
            </div>
            
            <button class="extract-btn" onclick="extractSource()">
                <span>🔍</span> Extract Source Code
            </button>
            
            <div id="result" class="result"></div>
            
            <div class="features">
                <div class="feature">
                    <div class="feature-icon">🚀</div>
                    <h3>Fast Extraction</h3>
                    <p>Quickly extract HTML source from static and dynamic websites</p>
                </div>
                
                <div class="feature">
                    <div class="feature-icon">🛡️</div>
                    <h3>Bypass Protection</h3>
                    <p>Bypass bot detection and InfinityFree protection systems</p>
                </div>
                
                <div class="feature">
                    <div class="feature-icon">⚡</div>
                    <h3>JavaScript Support</h3>
                    <p>Extract fully rendered content from React, Vue, Angular sites</p>
                </div>
                
                <div class="feature">
                    <div class="feature-icon">📥</div>
                    <h3>Direct Download</h3>
                    <p>Download extracted source as clean HTML file instantly</p>
                </div>
            </div>
            
            <div class="api-info">
                <h3>📡 API Usage</h3>
                <p>Use our API to extract source code programmatically:</p>
                <code>GET /api/protected?url=https://example.com</code>
                
                <p>Example with curl:</p>
                <code>curl "https://hs-websource-api.vercel.app/api/protected?url=https://zalim.kesug.com" --output source.html</code>
            </div>
            
            <div class="footer">
                <p>Powered by FastAPI & Playwright • Developer: Haseeb Sahil</p>
                <p>Telegram: @HS_WebSource_Bot • Channel: @hsmodzofc2</p>
            </div>
        </div>
        
        <script>
            function setUrl(url) {
                document.getElementById('urlInput').value = url;
            }
            
            async function extractSource() {
                const url = document.getElementById('urlInput').value.trim();
                const resultDiv = document.getElementById('result');
                
                if (!url) {
                    alert('Please enter a website URL');
                    return;
                }
                
                if (!url.startsWith('http')) {
                    alert('Please enter a valid URL starting with http:// or https://');
                    return;
                }
                
                resultDiv.className = 'result loading';
                resultDiv.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div style="font-size: 24px;">⏳</div>
                        <div>
                            <strong>Extracting source code...</strong>
                            <p style="margin-top: 5px; font-size: 0.9em; opacity: 0.8;">
                                This may take 10-20 seconds for JavaScript-heavy websites
                            </p>
                        </div>
                    </div>
                `;
                resultDiv.style.display = 'block';
                
                try {
                    const response = await fetch(`/api/protected?url=${encodeURIComponent(url)}`);
                    
                    if (response.ok) {
                        const blob = await response.blob();
                        
                        // Create download link
                        const downloadUrl = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = downloadUrl;
                        a.download = `extracted-${new URL(url).hostname}.html`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        
                        // Show success message
                        resultDiv.className = 'result success';
                        resultDiv.innerHTML = `
                            <div style="display: flex; align-items: center; gap: 15px;">
                                <div style="font-size: 24px;">✅</div>
                                <div>
                                    <strong>Source extracted successfully!</strong>
                                    <p style="margin-top: 5px;">Download started automatically</p>
                                </div>
                            </div>
                        `;
                        
                        // Show preview after download
                        setTimeout(async () => {
                            const text = await blob.text();
                            const preview = text.substring(0, 500) + (text.length > 500 ? '...' : '');
                            resultDiv.innerHTML += `
                                <hr style="margin: 20px 0; border: none; border-top: 1px solid #4CAF50;">
                                <details>
                                    <summary style="cursor: pointer; font-weight: bold;">Preview first 500 characters</summary>
                                    <pre style="margin-top: 10px; padding: 15px; background: white; border-radius: 8px; overflow: auto; font-size: 12px;">${escapeHtml(preview)}</pre>
                                </details>
                            `;
                        }, 1000);
                        
                    } else {
                        const error = await response.text();
                        resultDiv.className = 'result error';
                        resultDiv.innerHTML = `
                            <div style="display: flex; align-items: center; gap: 15px;">
                                <div style="font-size: 24px;">❌</div>
                                <div>
                                    <strong>Extraction Failed</strong>
                                    <p style="margin-top: 5px;">${error}</p>
                                </div>
                            </div>
                        `;
                    }
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.innerHTML = `
                        <div style="display: flex; align-items: center; gap: 15px;">
                            <div style="font-size: 24px;">❌</div>
                            <div>
                                <strong>Network Error</strong>
                                <p style="margin-top: 5px;">${error.message}</p>
                            </div>
                        </div>
                    `;
                }
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            // Enter key support
            document.getElementById('urlInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    extractSource();
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

@app.get("/api/protected")
async def protected_extract(url: str = Query(..., description="URL to extract source from")):
    """Extract source code from any website"""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        # Get full source code
        source_code, source_url = await extractor.get_full_source(url)
        
        if not source_code:
            raise HTTPException(
                status_code=404, 
                detail="Could not extract source code. The website might be blocking automated access or requires JavaScript."
            )
        
        # Add metadata header
        clean_html = f"""<!--
Extracted from: {url}
Source URL: {source_url}
Time: {datetime.now().isoformat()}
Powered by: Web Source Extractor Pro
Developer: Haseeb Sahil
Channel: @hsmodzofc2
Note: This is the fully rendered HTML including JavaScript-generated content
-->

{source_code}
"""
        
        # Return as downloadable file
        return Response(
            content=clean_html,
            media_type="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="extracted-{urlparse(url).netloc}.html"',
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
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, follow_redirects=True)
            
            content = response.text
            headers = dict(response.headers)
            
            # Check patterns
            is_protected = 'aes.js' in content or 'slowAES.decrypt' in content
            has_js = '<script' in content.lower()
            
            return JSONResponse({
                "url": str(response.url),
                "status_code": response.status_code,
                "content_length": len(content),
                "is_protected": is_protected,
                "has_javascript": has_js,
                "content_preview": content[:300] + "..." if len(content) > 300 else content,
                "headers": {k: v for k, v in headers.items() if k.lower() not in ['set-cookie', 'cookie']}
            })
            
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await extractor.close()

# For Vercel deployment
async def handler(request):
    return app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)