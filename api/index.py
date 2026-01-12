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

app = FastAPI(
    title="InfinityFree Direct File Access",
    description="Directly access uploaded files from InfinityFree hosting",
    version="14.0.0"
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

class DirectFileAccessor:
    def __init__(self):
        self.cache = {}
    
    async def get_file_content_directly(self, url: str):
        """
        Try to get file content directly without protection
        InfinityFree stores files in specific directories
        """
        print(f"\n{'='*60}")
        print(f"Direct File Access for: {url}")
        print(f"{'='*60}")
        
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path
        
        # Extract filename
        filename = os.path.basename(path) if path else 'index.html'
        
        print(f"Domain: {domain}")
        print(f"Path: {path}")
        print(f"Filename: {filename}")
        
        # Common InfinityFree upload directories
        common_dirs = [
            '',  # Root
            '/public_html',
            '/htdocs', 
            '/www',
            '/files',
            '/uploads',
            '/web',
            '/home',
        ]
        
        # Try different access patterns
        access_patterns = []
        
        # Pattern 1: Direct file access
        for dir_path in common_dirs:
            access_patterns.append(f"https://{domain}{dir_path}{path}")
            access_patterns.append(f"http://{domain}{dir_path}{path}")
        
        # Pattern 2: With common extensions
        for ext in ['.html', '.htm', '.php', '.txt', '.js', '.css']:
            if not path.endswith(ext):
                access_patterns.append(f"https://{domain}{path}{ext}")
        
        # Pattern 3: Try different filename variations
        name_parts = filename.split('.')
        if len(name_parts) > 1:
            base_name = '.'.join(name_parts[:-1])
            for ext in ['.html', '.htm', '.php']:
                access_patterns.append(f"https://{domain}{os.path.dirname(path)}/{base_name}{ext}")
        
        # Pattern 4: Try user directory patterns (common in InfinityFree)
        username = domain.split('.')[0] if '.' in domain else domain
        user_dirs = [
            f"https://{domain}/~{username}{path}",
            f"https://{domain}/{username}{path}",
            f"https://{domain}/home/{username}/public_html{path}",
            f"https://{domain}/home/{username}/htdocs{path}",
        ]
        access_patterns.extend(user_dirs)
        
        # Remove duplicates
        access_patterns = list(set(access_patterns))
        
        print(f"\nTrying {len(access_patterns)} direct access patterns...")
        
        for i, pattern_url in enumerate(access_patterns[:50]):  # Limit to 50
            try:
                print(f"  [{i+1}] Trying: {pattern_url}")
                
                async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                    # Try with different headers
                    headers_list = [
                        {'Accept': 'text/plain'},
                        {'Accept': 'text/html'},
                        {'Accept': '*/*'},
                        {'User-Agent': 'curl/7.68.0'},  # Simple curl
                        {'User-Agent': 'Wget/1.20.3'},   # Wget
                    ]
                    
                    for headers in headers_list:
                        try:
                            response = await client.get(pattern_url, headers=headers)
                            
                            if response.status_code == 200:
                                content = response.text
                                
                                # Check if it's actual content (not protection)
                                if ('aes.js' not in content and 
                                    'trap for bots' not in content.lower() and
                                    'content loading' not in content.lower() and
                                    len(content) > 10):  # Even small files are OK
                                    
                                    print(f"  ✓ Found at: {pattern_url}")
                                    print(f"    Content length: {len(content)}")
                                    print(f"    Content-Type: {response.headers.get('content-type', 'unknown')}")
                                    
                                    return content, pattern_url
                            
                            await asyncio.sleep(0.2)
                        except:
                            continue
                    
            except Exception as e:
                continue
        
        return None, None
    
    async def try_file_download(self, url: str):
        """
        Try to trigger file download instead of viewing
        """
        print(f"\n[Method 2] Trying file download approach...")
        
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path
        
        # Try download parameters
        download_patterns = [
            f"https://{domain}{path}?download",
            f"https://{domain}{path}?download=1",
            f"https://{domain}{path}?force_download",
            f"https://{domain}{path}?raw",
            f"https://{domain}{path}?raw=1",
            f"https://{domain}{path}?source",
            f"https://{domain}{path}?view=source",
            f"https://{domain}{path}?show_source",
        ]
        
        for pattern_url in download_patterns:
            try:
                print(f"  Trying download: {pattern_url}")
                
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.get(pattern_url)
                    
                    if response.status_code == 200:
                        content = response.text
                        
                        # Check headers for download
                        content_disposition = response.headers.get('content-disposition', '').lower()
                        
                        if ('attachment' in content_disposition or 
                            'download' in content_disposition or
                            ('aes.js' not in content and 
                             'trap for bots' not in content.lower())):
                            
                            print(f"  ✓ Download successful: {pattern_url}")
                            return content, pattern_url
                    
                    await asyncio.sleep(0.5)
            except:
                continue
        
        return None, None
    
    async def try_directory_traversal(self, url: str):
        """
        Try to access files through directory traversal
        """
        print(f"\n[Method 3] Trying directory traversal...")
        
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path
        
        # Common directory traversal patterns
        traversal_patterns = []
        
        # Try to go up directories
        dir_parts = path.split('/')
        for i in range(1, min(4, len(dir_parts))):
            parent_path = '/'.join(dir_parts[:-i])
            if parent_path:
                traversal_patterns.append(f"https://{domain}{parent_path}/")
        
        # Try common file locations
        common_files = [
            'index.html', 'index.php', 'index.htm',
            'default.html', 'default.php',
            'home.html', 'home.php',
            'main.html', 'main.php',
        ]
        
        for file in common_files:
            traversal_patterns.append(f"https://{domain}/{file}")
            traversal_patterns.append(f"https://{domain}/public_html/{file}")
            traversal_patterns.append(f"https://{domain}/htdocs/{file}")
        
        for pattern_url in traversal_patterns:
            try:
                print(f"  Trying traversal: {pattern_url}")
                
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(pattern_url)
                    
                    if response.status_code == 200:
                        content = response.text
                        
                        if ('aes.js' not in content and 
                            'trap for bots' not in content.lower() and
                            len(content) > 100):
                            
                            print(f"  ✓ Found via traversal: {pattern_url}")
                            return content, pattern_url
                    
                    await asyncio.sleep(0.5)
            except:
                continue
        
        return None, None
    
    async def extract_uploaded_file(self, url: str):
        """
        Main method to extract uploaded file
        """
        # Method 1: Direct file access
        print(f"\n[Method 1] Direct file access...")
        content1, url1 = await self.get_file_content_directly(url)
        
        if content1:
            return content1, url1
        
        # Method 2: File download approach
        print(f"\n[Method 2] File download...")
        content2, url2 = await self.try_file_download(url)
        
        if content2:
            return content2, url2
        
        # Method 3: Directory traversal
        print(f"\n[Method 3] Directory traversal...")
        content3, url3 = await self.try_directory_traversal(url)
        
        if content3:
            return content3, url3
        
        # Method 4: Try to brute force common files
        print(f"\n[Method 4] Brute forcing common files...")
        content4, url4 = await self.brute_force_common_files(url)
        
        if content4:
            return content4, url4
        
        print(f"\n✗ All file access methods failed")
        return None, None
    
    async def brute_force_common_files(self, url: str):
        """
        Brute force common file names and locations
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path
        
        # Extract potential file name
        if path and path != '/':
            base_name = os.path.basename(path)
            if '.' in base_name:
                name_parts = base_name.split('.')
                base = '.'.join(name_parts[:-1])
                ext = name_parts[-1]
            else:
                base = base_name
                ext = ''
        else:
            base = 'index'
            ext = 'html'
        
        # Common file variations to try
        file_variations = []
        
        # Try different extensions
        for new_ext in ['html', 'htm', 'php', 'txt', 'js', 'css', 'xml', 'json']:
            file_variations.append(f"{base}.{new_ext}")
        
        # Try different prefixes/suffixes
        prefixes = ['', 'main.', 'home.', 'index.', 'default.', 'page.']
        suffixes = ['', '.old', '.bak', '.backup', '.copy', '.original']
        
        for prefix in prefixes:
            for suffix in suffixes:
                for ext in ['html', 'htm', 'php']:
                    file_variations.append(f"{prefix}{base}{suffix}.{ext}")
        
        # Remove duplicates
        file_variations = list(set(file_variations))
        
        # Common directories
        directories = ['', '/public_html', '/htdocs', '/www', '/files']
        
        print(f"Brute forcing {len(file_variations)} file names in {len(directories)} directories...")
        
        for directory in directories:
            for filename in file_variations[:100]:  # Limit to 100
                try:
                    test_url = f"https://{domain}{directory}/{filename}"
                    
                    async with httpx.AsyncClient(timeout=5) as client:
                        response = await client.get(test_url)
                        
                        if response.status_code == 200:
                            content = response.text
                            
                            if ('aes.js' not in content and 
                                'trap for bots' not in content.lower() and
                                len(content) > 10):
                                
                                print(f"  ✓ Found: {test_url}")
                                return content, test_url
                        
                        await asyncio.sleep(0.1)
                except:
                    continue
        
        return None, None
    
    async def analyze_file_structure(self, url: str):
        """
        Analyze the file structure to understand what's uploaded
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        
        analysis = {
            'domain': domain,
            'tested_urls': [],
            'accessible_files': [],
            'directory_listings': [],
        }
        
        # Test common endpoints
        test_endpoints = [
            f"https://{domain}/",
            f"https://{domain}/public_html/",
            f"https://{domain}/htdocs/",
            f"https://{domain}/www/",
            f"https://{domain}/files/",
            f"https://{domain}/uploads/",
            f"https://{domain}/.git/",  # Git directory
            f"https://{domain}/wp-admin/",  # WordPress
            f"https://{domain}/wp-content/",  # WordPress content
            f"https://{domain}/admin/",  # Admin panel
            f"https://{domain}/cgi-bin/",  # CGI directory
        ]
        
        for endpoint in test_endpoints:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(endpoint)
                    
                    analysis['tested_urls'].append({
                        'url': endpoint,
                        'status': response.status_code,
                        'content_type': response.headers.get('content-type'),
                        'content_length': len(response.text),
                    })
                    
                    # Check for directory listing
                    if ('Index of' in response.text or 
                        '[To Parent Directory]' in response.text or
                        '<title>Index of' in response.text):
                        analysis['directory_listings'].append(endpoint)
                    
                    await asyncio.sleep(0.5)
            except Exception as e:
                analysis['tested_urls'].append({
                    'url': endpoint,
                    'error': str(e)
                })
        
        return analysis

file_accessor = DirectFileAccessor()

@app.get("/")
async def home():
    return templates.TemplateResponse("index.html", {"request": {}})

@app.get("/api/recover")
async def recover_source(url: str = Query(..., description="InfinityFree URL to recover source from")):
    """Recover original uploaded file content"""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        print(f"\n{'='*60}")
        print(f"FILE RECOVERY REQUEST: {url}")
        print(f"Time: {datetime.now().isoformat()}")
        print(f"{'='*60}")
        
        # Extract uploaded file
        source_code, source_url = await file_accessor.extract_uploaded_file(url)
        
        if not source_code:
            raise HTTPException(
                status_code=404, 
                detail="Could not access the uploaded file. It might be protected or not directly accessible."
            )
        
        # Check if it's trap content
        if ('trap for bots' in source_code.lower() or 
            'content loading' in source_code.lower()):
            
            raise HTTPException(
                status_code=404,
                detail="Found bot trap content. The actual file might be in a different location or protected."
            )
        
        # Create recovered file
        clean_html = f"""<!DOCTYPE html>
<!--
Recovered from: {url}
Actual Source URL: {source_url}
Recovery Time: {datetime.now().isoformat()}
Tool: InfinityFree Direct File Access v14.0
Note: This is the actual uploaded file content
-->

{source_code}
"""
        
        # Return as downloadable file
        return Response(
            content=clean_html,
            media_type="text/html",
            headers={
                "Content-Disposition": "attachment; filename=recovered-original-file.html",
                "Content-Type": "text/html; charset=utf-8",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"File recovery failed: {str(e)}")

@app.get("/api/analyze-structure")
async def analyze_structure(url: str = Query(..., description="URL to analyze file structure")):
    """Analyze the file structure of an InfinityFree site"""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        analysis = await file_accessor.analyze_file_structure(url)
        
        return JSONResponse({
            'analysis': analysis,
            'recommendations': [
                'Check directory listings for accessible files',
                'Try common file locations like /public_html/, /htdocs/',
                'Common files: index.html, index.php, main.html, etc.'
            ]
        })
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/find-files")
async def find_files(url: str = Query(..., description="Base URL to find files")):
    """Find accessible files on an InfinityFree site"""
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Common files to check
        common_files = [
            'index.html', 'index.php', 'index.htm',
            'default.html', 'default.php',
            'home.html', 'home.php',
            'main.html', 'main.php',
            'style.css', 'styles.css',
            'script.js', 'main.js',
            'config.php', 'settings.php',
            'robots.txt', 'sitemap.xml',
            '.htaccess', 'web.config',
        ]
        
        # Directories to check
        directories = ['', '/public_html', '/htdocs', '/www', '/files', '/uploads']
        
        results = []
        
        for directory in directories:
            for filename in common_files:
                test_url = f"https://{domain}{directory}/{filename}"
                
                try:
                    async with httpx.AsyncClient(timeout=5) as client:
                        response = await client.get(test_url)
                        
                        result = {
                            'url': test_url,
                            'status': response.status_code,
                            'content_type': response.headers.get('content-type'),
                            'content_length': len(response.text),
                            'has_protection': 'aes.js' in response.text,
                            'has_trap': 'trap for bots' in response.text.lower(),
                            'is_accessible': (response.status_code == 200 and 
                                            'aes.js' not in response.text and
                                            'trap for bots' not in response.text.lower())
                        }
                        
                        if result['is_accessible']:
                            result['content_preview'] = response.text[:200] + "..." if len(response.text) > 200 else response.text
                        
                        results.append(result)
                        
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    results.append({
                        'url': test_url,
                        'error': str(e)
                    })
        
        # Filter accessible files
        accessible_files = [r for r in results if r.get('is_accessible')]
        
        return JSONResponse({
            'domain': domain,
            'tested_files': len(results),
            'accessible_files': accessible_files,
            'all_results': results
        })
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/debug-file")
async def debug_file(url: str = Query(..., description="File URL to debug")):
    """Debug file access"""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, follow_redirects=True)
            
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path) if parsed.path else 'unknown'
            
            debug_info = {
                "requested_url": url,
                "final_url": str(response.url),
                "filename": filename,
                "status_code": response.status_code,
                "content_length": len(response.text),
                "content_type": response.headers.get('content-type'),
                "headers": dict(response.headers),
                "has_aes_protection": 'aes.js' in response.text,
                "has_trap_content": 'trap for bots' in response.text.lower() or 'content loading' in response.text.lower(),
                "content_preview": response.text[:1000] + "..." if len(response.text) > 1000 else response.text,
                "recommendations": [
                    "Try accessing file through /public_html/ or /htdocs/ directory",
                    "Try adding ?download or ?raw parameter",
                    "Check if file exists with different extension (.html, .php, .htm)"
                ]
            }
            
            return JSONResponse(debug_info)
            
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/protected")
async def extract_protected_content(url: str = Query(..., description="Protected URL to extract from")):
    """Legacy endpoint - redirects to recover"""
    return await recover_source(url)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.index:app", host="0.0.0.0", port=8000, reload=True)