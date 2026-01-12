from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response, JSONResponse, HTMLResponse
import httpx
import asyncio
import re
import time
from urllib.parse import urljoin, urlparse
from datetime import datetime

app = FastAPI(
    title="Web Source Extractor",
    description="Extract HTML source code from any website",
    version="3.0.0"
)

class SmartSourceExtractor:
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
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                }
            )
        return self.client
    
    async def extract_html(self, url: str):
        """Smart HTML extraction with multiple methods"""
        print(f"📡 Extracting: {url}")
        
        client = await self.get_client()
        
        # Method 1: Direct fetch
        try:
            response = await client.get(url)
            content = response.text
            
            # Check if it's a valid HTML page
            if self.is_valid_html(content):
                print("✅ Method 1: Direct fetch successful")
                return content, str(response.url)
        except Exception as e:
            print(f"❌ Method 1 failed: {e}")
        
        # Method 2: Try with different user agents
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Googlebot/2.1 (+http://www.google.com/bot.html)',
            'Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)'
        ]
        
        for ua in user_agents:
            try:
                headers = {'User-Agent': ua}
                response = await client.get(url, headers=headers)
                content = response.text
                
                if self.is_valid_html(content):
                    print(f"✅ Method 2: UA {ua[:30]}... successful")
                    return content, str(response.url)
            except:
                continue
        
        # Method 3: Try different URL variations
        parsed = urlparse(url)
        variations = [
            url,
            url.replace('https://', 'http://'),
            url + '?i=1',
            url + '?nocache=1',
            url + f'?t={int(time.time())}',
            url + '&t=' + str(int(time.time())),
            f"http://{parsed.netloc}{parsed.path}",
            f"https://{parsed.netloc}/public_html{parsed.path}",
            f"https://{parsed.netloc}/htdocs{parsed.path}",
        ]
        
        for var_url in variations:
            try:
                response = await client.get(var_url)
                content = response.text
                
                if self.is_valid_html(content):
                    print(f"✅ Method 3: URL variation successful")
                    return content, str(response.url)
            except:
                continue
        
        print("❌ All methods failed")
        return None, None
    
    def is_valid_html(self, content: str):
        """Check if content is valid HTML"""
        if not content or len(content.strip()) < 100:
            return False
        
        # Check for HTML tags
        html_indicators = ['<!DOCTYPE', '<html', '<head', '<body', '<div', '<p>']
        has_html = any(indicator in content[:500].lower() for indicator in [i.lower() for i in html_indicators])
        
        if not has_html:
            return False
        
        # Check for bot traps
        trap_indicators = [
            'this is a trap for bots',
            'content loading...',
            'please wait...',
            'you are being redirected',
        ]
        
        for trap in trap_indicators:
            if trap in content[:1000].lower():
                return False
        
        return True
    
    async def close(self):
        if self.client:
            await self.client.aclose()

# Create extractor instance
extractor = SmartSourceExtractor()

@app.get("/")
async def home():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Web Source Extractor</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
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
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                width: 100%;
                max-width: 800px;
            }
            
            .header {
                text-align: center;
                margin-bottom: 30px;
            }
            
            h1 {
                color: #333;
                font-size: 2.5em;
                margin-bottom: 10px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .tagline {
                color: #666;
                font-size: 1.1em;
                margin-bottom: 20px;
            }
            
            .input-group {
                margin-bottom: 20px;
            }
            
            input[type="url"] {
                width: 100%;
                padding: 15px;
                font-size: 16px;
                border: 2px solid #ddd;
                border-radius: 10px;
                transition: all 0.3s;
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
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
                cursor: pointer;
                width: 100%;
                transition: all 0.3s;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }
            
            .extract-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }
            
            .result {
                margin-top: 20px;
                padding: 15px;
                border-radius: 10px;
                display: none;
            }
            
            .loading {
                background: #e3f2fd;
                border: 2px solid #2196f3;
                color: #1565c0;
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
            
            .features {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin-top: 30px;
            }
            
            .feature {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
            }
            
            .feature-icon {
                font-size: 2em;
                margin-bottom: 10px;
            }
            
            .api-info {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                margin-top: 20px;
            }
            
            code {
                background: #333;
                color: white;
                padding: 10px;
                border-radius: 5px;
                display: block;
                margin: 10px 0;
                font-family: monospace;
                overflow-x: auto;
                font-size: 14px;
            }
            
            .test-urls {
                display: flex;
                gap: 10px;
                margin-top: 15px;
                flex-wrap: wrap;
            }
            
            .test-btn {
                background: #e3f2fd;
                color: #1565c0;
                border: 1px solid #bbdefb;
                padding: 8px 15px;
                border-radius: 20px;
                cursor: pointer;
                transition: all 0.3s;
                font-size: 14px;
            }
            
            .test-btn:hover {
                background: #bbdefb;
            }
            
            .footer {
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                color: #666;
                font-size: 0.9em;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌐 Web Source Extractor</h1>
                <p class="tagline">Extract HTML source code from any website</p>
            </div>
            
            <div class="input-group">
                <input type="url" id="urlInput" 
                       placeholder="Enter website URL (e.g., https://example.com)" 
                       value="https://zalim.kesug.com">
                <div class="test-urls">
                    <button class="test-btn" onclick="setUrl('https://zalim.kesug.com')">Test Site</button>
                    <button class="test-btn" onclick="setUrl('https://google.com')">Google</button>
                    <button class="test-btn" onclick="setUrl('https://github.com')">GitHub</button>
                </div>
            </div>
            
            <button class="extract-btn" onclick="extractSource()">
                <span>🔍</span> Extract Source Code
            </button>
            
            <div id="result" class="result"></div>
            
            <div class="features">
                <div class="feature">
                    <div class="feature-icon">⚡</div>
                    <h3>Fast Extraction</h3>
                    <p>Quick HTML source extraction</p>
                </div>
                
                <div class="feature">
                    <div class="feature-icon">🛡️</div>
                    <h3>Smart Bypass</h3>
                    <p>Multiple bypass techniques</p>
                </div>
                
                <div class="feature">
                    <div class="feature-icon">📥</div>
                    <h3>Direct Download</h3>
                    <p>Download as HTML file</p>
                </div>
                
                <div class="feature">
                    <div class="feature-icon">🔧</div>
                    <h3>Simple API</h3>
                    <p>Easy to use API</p>
                </div>
            </div>
            
            <div class="api-info">
                <h3>📡 API Usage</h3>
                <code>GET /api/extract?url=https://example.com</code>
                <code>curl "https://hs-websource-api.vercel.app/api/extract?url=https://example.com" -o source.html</code>
            </div>
            
            <div class="footer">
                <p>Developer: Haseeb Sahil | Telegram: @HS_WebSource_Bot</p>
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
                
                resultDiv.className = 'result loading';
                resultDiv.innerHTML = '⏳ Extracting source code...';
                resultDiv.style.display = 'block';
                
                try {
                    const response = await fetch(`/api/extract?url=${encodeURIComponent(url)}`);
                    
                    if (response.ok) {
                        const blob = await response.blob();
                        
                        // Create download link
                        const downloadUrl = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = downloadUrl;
                        a.download = `source-${new URL(url).hostname}.html`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        
                        resultDiv.className = 'result success';
                        resultDiv.innerHTML = '✅ Source extracted! Download started.';
                    } else {
                        const error = await response.text();
                        resultDiv.className = 'result error';
                        resultDiv.innerHTML = `❌ Error: ${error}`;
                    }
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.innerHTML = `❌ Network error: ${error.message}`;
                }
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

@app.get("/api/extract")
async def extract_source(url: str = Query(..., description="URL to extract source from")):
    """Extract source code from any website"""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        # Get source code
        source_code, source_url = await extractor.extract_html(url)
        
        if not source_code:
            raise HTTPException(
                status_code=404, 
                detail="Could not extract source code. The website might be blocking access."
            )
        
        # Add metadata header
        clean_html = f"""<!--
Extracted from: {url}
Source URL: {source_url}
Time: {datetime.now().isoformat()}
Powered by: Web Source Extractor
Developer: Haseeb Sahil
Channel: @hsmodzofc2
-->

{source_code}
"""
        
        # Return as downloadable file
        return Response(
            content=clean_html,
            media_type="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="source-{urlparse(url).netloc}.html"',
                "Content-Type": "text/html; charset=utf-8",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    await extractor.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)=