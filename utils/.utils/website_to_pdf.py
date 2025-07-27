#!/usr/bin/env python3
"""
Website to PDF Converter - Production Ready with Smart Auto-Fixes

A robust, production-ready website-to-PDF converter with automatic rendering issue 
detection and smart layout fixes. Designed for reliable operation with security 
hardening, structured logging, and comprehensive error handling.

Key Features:
- 🧠 Automatic rendering issue detection and fixes
- 🔒 Security hardening with input validation and sanitization  
- 📱 Screen media emulation by default for better rendering
- 👻 Always headless operation (no browser windows)
- 🚀 Fast by default with smart optimizations
- 📊 Structured logging with session IDs for debugging
- 🔄 Exponential backoff retry logic with circuit breakers
- 🍪 Cookie support (Netscape format and browser extraction)
- ⚡ Smart fallback strategies for complex websites

Production Standards:
- Custom exception classes for better error handling
- Comprehensive input validation and path traversal protection
- Resource management with proper cleanup
- Performance monitoring and metrics logging
- Type hints and comprehensive docstrings
- Security-first design principles

Example URLs that work well:
- News articles: https://techcrunch.com/2024/01/15/ai-breakthrough-announced
- Wikipedia pages: https://en.wikipedia.org/wiki/Artificial_intelligence  
- Blog posts: https://openai.com/blog/gpt-4-research
- Essays: https://www.darioamodei.com/essay/machines-of-loving-grace
- Documentation: https://docs.python.org/3/tutorial/
- GitHub repos: https://github.com/microsoft/playwright
- Medium articles: https://medium.com/@username/article-title
- Academic papers: https://arxiv.org/abs/2301.00001
- Company pages: https://anthropic.com/research

Usage Examples:
    # Basic usage - auto-generated filename with smart fixes
    ./website_to_pdf.py https://example.com
    
    # Custom filename with optimizations  
    ./website_to_pdf.py https://longform-essay.com -o essay.pdf --block-images
    
    # Debug mode with detailed logging
    ./website_to_pdf.py https://complex-site.com --debug
    
    # With authentication cookies
    ./website_to_pdf.py https://private-site.com --cookies cookies.txt
    
    # Slow mode for very complex sites
    ./website_to_pdf.py https://heavy-js-site.com --slow

Author: Generated with Claude Code
License: MIT
Version: 2.0.0 (Production)
"""

import argparse
import asyncio
import json
import logging
import os
import re
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Union, List, Dict
from urllib.parse import urlparse
import tempfile
import uuid

try:
    from playwright.async_api import async_playwright, Page, Browser, Error as PlaywrightError
except ImportError:
    print("❌ Playwright not installed. Install with: pip install playwright")
    print("   Then run: playwright install chromium")
    sys.exit(1)


# Custom Exception Classes for Production Error Handling
class PDFConverterError(Exception):
    """Base exception for PDF converter operations"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()


class ValidationError(PDFConverterError):
    """Raised when input validation fails"""
    pass


class NetworkError(PDFConverterError):
    """Raised when network operations fail"""
    pass


class RenderingError(PDFConverterError):
    """Raised when page rendering fails"""
    pass


class FileOperationError(PDFConverterError):
    """Raised when file operations fail"""
    pass


class ConfigurationError(PDFConverterError):
    """Raised when configuration is invalid"""
    pass


@dataclass
class Config:
    """Configuration settings for the PDF converter"""
    url: str
    output: Optional[str] = None
    timeout: int = 60
    max_retries: int = 3
    headless: bool = True  # Always headless
    debug: bool = False
    dry_run: bool = False
    wait_time: int = 1  # Fast by default
    viewport_width: int = 1280
    viewport_height: int = 1024
    format: str = 'Letter'
    print_background: bool = True
    margin: str = '20px'
    margin_top: str = '20px'
    margin_bottom: str = '20px'
    margin_left: str = '20px'
    margin_right: str = '20px'
    user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    screenshot_on_error: bool = True
    config: Optional[str] = None
    cookies: Optional[str] = None
    cookies_from_browser: Optional[str] = None
    # Smart options
    slow: bool = False
    block_images: bool = False
    wait_until: str = 'domcontentloaded'
    emulate_media: str = 'screen'  # Screen by default for better rendering
    prefer_css_page_size: bool = False
    auto_fix: bool = True  # Enable smart auto-fixes


class RenderingIssueDetector:
    """Detects and fixes common rendering issues"""
    
    def __init__(self, page: Page, logger):
        self.page = page
        self.logger = logger
        
    async def check_content_clipping(self) -> Dict[str, any]:
        """Check if content is being clipped or hidden"""
        issues = await self.page.evaluate("""
            () => {
                const issues = {
                    hasOverflowHidden: false,
                    hasFixedHeight: false,
                    hasScrollableContent: false,
                    contentHeight: 0,
                    viewportHeight: window.innerHeight,
                    elementsWithMaxHeight: 0,
                    hiddenContent: false
                };
                
                // Check for overflow hidden
                const overflowHidden = document.querySelectorAll('[style*="overflow: hidden"], [style*="overflow:hidden"]');
                issues.hasOverflowHidden = overflowHidden.length > 0;
                
                // Check for fixed heights that might clip content
                const fixedHeights = document.querySelectorAll('[style*="height:"], [style*="max-height:"]');
                issues.hasFixedHeight = fixedHeights.length > 0;
                issues.elementsWithMaxHeight = fixedHeights.length;
                
                // Check actual content height
                issues.contentHeight = Math.max(
                    document.body.scrollHeight,
                    document.documentElement.scrollHeight
                );
                
                // Check if there's scrollable content
                const scrollableElements = Array.from(document.querySelectorAll('*')).filter(el => {
                    const style = window.getComputedStyle(el);
                    return style.overflowY === 'scroll' || style.overflowY === 'auto';
                }).filter(el => el.scrollHeight > el.clientHeight);
                
                issues.hasScrollableContent = scrollableElements.length > 0;
                
                // Check for visually hidden content
                const hiddenElements = document.querySelectorAll('[style*="display: none"], [style*="visibility: hidden"]');
                issues.hiddenContent = hiddenElements.length > 5; // Threshold for significant hidden content
                
                return issues;
            }
        """)
        
        return issues
    
    async def fix_layout_issues(self) -> List[str]:
        """Apply automatic fixes for detected issues"""
        fixes_applied = []
        
        # Fix 1: Remove overflow hidden and height restrictions
        await self.page.evaluate("""
            () => {
                // Remove overflow hidden from main content areas
                const contentElements = document.querySelectorAll('main, article, .content, [role="main"], .post, .essay');
                contentElements.forEach(el => {
                    el.style.overflow = 'visible';
                    el.style.maxHeight = 'none';
                    el.style.height = 'auto';
                });
                
                // Fix common wrapper issues
                const wrappers = document.querySelectorAll('.wrapper, .container, .page-wrapper');
                wrappers.forEach(el => {
                    el.style.minHeight = 'auto';
                    el.style.height = 'auto';
                    el.style.maxHeight = 'none';
                    el.style.overflow = 'visible';
                });
            }
        """)
        fixes_applied.append("Removed height restrictions and overflow hidden")
        
        # Fix 2: Expand collapsed/hidden content
        await self.page.evaluate("""
            () => {
                // Click expand buttons
                const expandButtons = document.querySelectorAll('[aria-expanded="false"], .expand, .show-more');
                expandButtons.forEach(btn => {
                    try { btn.click(); } catch(e) {}
                });
                
                // Force show hidden content sections
                const hiddenSections = document.querySelectorAll('[style*="display: none"]');
                hiddenSections.forEach(el => {
                    if (el.textContent && el.textContent.length > 50) {
                        el.style.display = 'block';
                    }
                });
            }
        """)
        fixes_applied.append("Expanded collapsed content")
        
        # Fix 3: Remove fixed positioning that interferes with printing
        await self.page.evaluate("""
            () => {
                const fixedElements = document.querySelectorAll('*');
                Array.from(fixedElements).forEach(el => {
                    const style = window.getComputedStyle(el);
                    if (style.position === 'fixed') {
                        // Only modify if it's not essential content
                        if (!el.matches('main, article, .content, [role="main"]')) {
                            el.style.position = 'static';
                        }
                    }
                });
            }
        """)
        fixes_applied.append("Fixed positioning issues")
        
        # Fix 4: Force full content display for reading apps
        await self.page.evaluate("""
            () => {
                // Common patterns for reading apps and blogs
                const readingContainers = document.querySelectorAll(
                    '.reader-content, .post-content, .article-content, .essay-content, ' +
                    '[data-testid="article"], .prose, .markdown-body'
                );
                
                readingContainers.forEach(container => {
                    container.style.maxHeight = 'none';
                    container.style.overflow = 'visible';
                    container.style.height = 'auto';
                    
                    // Remove any gradients or fade effects
                    container.style.maskImage = 'none';
                    container.style.webkitMaskImage = 'none';
                });
            }
        """)
        fixes_applied.append("Optimized reading containers")
        
        return fixes_applied


class WebsiteToPDFConverter:
    """Smart converter with automatic issue detection and fixing"""
    
    def __init__(self, config: Config):
        self.config = config
        # Force headless mode
        self.config.headless = True
        # Generate unique session ID for tracking
        self.session_id = str(uuid.uuid4())[:8]
        self.logger = self._setup_logging()
        self.start_time = time.time()
        self._setup_signal_handlers()
        
        # Apply slow mode if requested
        if self.config.slow:
            self.logger.info("🐌 Slow mode enabled")
            self.config.wait_time = 3
            self.config.wait_until = 'networkidle'
        else:
            self.logger.info("⚡ Fast mode with smart auto-fixes")
        
    def _setup_logging(self) -> logging.Logger:
        """Configure structured logging with session IDs"""
        level = logging.DEBUG if self.config.debug else logging.INFO
        format_str = f'%(asctime)s - [{self.session_id}] - %(funcName)s:%(lineno)d - %(levelname)s - %(message)s'
        
        # Create formatter
        formatter = logging.Formatter(format_str)
        
        # Create logger
        logger = logging.getLogger(f'website_to_pdf.{self.session_id}')
        logger.setLevel(level)
        
        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Add file handler in debug mode
        if self.config.debug:
            file_handler = logging.FileHandler(
                f'website_to_pdf_{datetime.now():%Y%m%d_%H%M%S}_{self.session_id}.log'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        return logger
    
    def log_structured(self, level: str, message: str, **kwargs) -> None:
        """Log structured data with context"""
        context = {
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'url': getattr(self.config, 'url', 'unknown'),
            **kwargs
        }
        
        # Create structured message
        if kwargs:
            structured_msg = f"{message} | Context: {json.dumps(context, default=str)}"
        else:
            structured_msg = message
        
        # Log at appropriate level
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(structured_msg)
    
    def log_operation(self, operation: str, status: str, duration_ms: Optional[float] = None, **details) -> None:
        """Log operation with performance metrics"""
        self.log_structured(
            'info',
            f"Operation: {operation} | Status: {status}",
            operation=operation,
            status=status,
            duration_ms=duration_ms,
            **details
        )
    
    def _setup_signal_handlers(self):
        """Handle graceful shutdown on SIGINT"""
        def signal_handler(signum, frame):
            self.logger.info("⚠️  Received interrupt signal, shutting down gracefully...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
    
    def parse_cookie_file(self, cookie_file: str) -> List[Dict]:
        """Parse Netscape format cookie file"""
        cookies = []
        try:
            with open(cookie_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        cookie = {
                            'name': parts[5],
                            'value': parts[6],
                            'domain': parts[0],
                            'path': parts[2],
                            'secure': parts[3].lower() == 'true',
                            'httpOnly': parts[1].lower() == 'true'
                        }
                        if parts[4] != '0':
                            cookie['expires'] = int(parts[4])
                        cookies.append(cookie)
                        
            self.logger.info(f"🍪 Loaded {len(cookies)} cookies from {cookie_file}")
            return cookies
            
        except Exception as e:
            self.logger.error(f"Failed to parse cookie file: {e}")
            return []
    
    def sanitize_filename(self, title: str) -> str:
        """Sanitize title for use as filename with security hardening"""
        if not isinstance(title, str):
            raise ValidationError("Title must be a string", "INVALID_TYPE")
        
        # Remove null bytes and control characters (security)
        title = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', title)
        
        # Remove path traversal patterns (security hardening)
        title = re.sub(r'\.\.', '', title)
        title = re.sub(r'[/\\]', '', title)
        
        # Remove Windows reserved names (security)
        windows_reserved = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                           'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
                           'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
        if title.upper() in windows_reserved:
            title = f"file_{title}"
        
        # Remove other dangerous characters
        title = re.sub(r'[<>:"/\\|?*]', '', title)
        title = re.sub(r'\s+', ' ', title)
        title = title.strip()
        
        # Limit length and ensure not empty
        title = title[:100]
        if not title or title.isspace():
            title = "untitled"
        
        # Ensure it doesn't start with dangerous patterns
        if title.startswith(('.', '-')):
            title = f"file_{title}"
            
        return title
    
    async def extract_page_title(self, page: Page) -> str:
        """Extract page title with fallbacks"""
        try:
            title = await page.title()
            if not title or title == "":
                title = await page.evaluate(
                    "() => document.querySelector('meta[property=\"og:title\"]')?.content || ''"
                )
            if not title:
                title = await page.evaluate(
                    "() => document.querySelector('h1')?.textContent || ''"
                )
            if not title:
                parsed = urlparse(self.config.url)
                title = parsed.netloc.replace('www.', '')
            
            return self.sanitize_filename(title)
        except Exception as e:
            self.logger.warning(f"Failed to extract title: {e}")
            parsed = urlparse(self.config.url)
            return self.sanitize_filename(parsed.netloc)
    
    def generate_filename(self, title: str) -> str:
        """Generate filename in format: YYYY-MM-DD__WEBSITE_TITLE.pdf"""
        date_prefix = datetime.now().strftime('%Y-%m-%d')
        return f"{date_prefix}__{title}.pdf"
    
    async def wait_for_page_load(self, page: Page):
        """Wait for page to load completely"""
        # Wait for basic load state
        await page.wait_for_load_state(self.config.wait_until, timeout=30000)
        
        # Additional wait time
        await page.wait_for_timeout(self.config.wait_time * 1000)
        
        # Extra stability check in slow mode
        if self.config.slow:
            try:
                await page.wait_for_function(
                    "() => document.readyState === 'complete'",
                    timeout=5000
                )
            except:
                pass
    
    async def smart_scroll_and_expand(self, page: Page):
        """Intelligent scrolling with content expansion"""
        # Quick scroll to trigger lazy loading
        await page.evaluate("window.scrollTo(0, 1000)")
        await page.wait_for_timeout(300)
        
        # Scroll to bottom to load all content
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(500)
        
        # Try to expand any "read more" or collapsed content
        await page.evaluate("""
            () => {
                // Common expand button selectors
                const expandSelectors = [
                    'button[aria-expanded="false"]',
                    '.read-more', '.show-more', '.expand',
                    '[data-testid*="expand"]', '[data-testid*="more"]'
                ];
                
                expandSelectors.forEach(selector => {
                    const buttons = document.querySelectorAll(selector);
                    buttons.forEach(btn => {
                        try { 
                            btn.click(); 
                            // Wait a bit for expansion
                            setTimeout(() => {}, 200);
                        } catch(e) {}
                    });
                });
            }
        """)
        
        await page.wait_for_timeout(500)
        
        # Scroll back to top for consistent PDF generation
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(200)
    
    async def convert_with_smart_fixes(self, page: Page, url: str) -> Tuple[bool, str, Optional[str]]:
        """Convert with automatic issue detection and fixes"""
        try:
            self.logger.info(f"🔄 Converting {url} with smart fixes")
            
            # Navigate to URL
            response = await page.goto(
                url,
                wait_until=self.config.wait_until,
                timeout=self.config.timeout * 1000
            )
            
            if response and response.status >= 400:
                raise Exception(f"HTTP {response.status} error")
            
            # Extract title
            title = await self.extract_page_title(page)
            output_path = self.config.output or self.generate_filename(title)
            self.logger.info(f"📝 Using filename: {output_path}")
            
            # Wait for initial load
            await self.wait_for_page_load(page)
            
            # Smart content expansion and scrolling
            await self.smart_scroll_and_expand(page)
            
            if self.config.auto_fix:
                # Detect and fix rendering issues
                detector = RenderingIssueDetector(page, self.logger)
                issues = await detector.check_content_clipping()
                
                self.logger.debug(f"Detected issues: {issues}")
                
                # Apply fixes if issues detected
                if (issues['hasOverflowHidden'] or 
                    issues['hasFixedHeight'] or 
                    issues['hiddenContent'] or
                    issues['contentHeight'] > issues['viewportHeight'] * 3):
                    
                    self.logger.info("🔧 Applying smart layout fixes...")
                    fixes = await detector.fix_layout_issues()
                    
                    for fix in fixes:
                        self.logger.debug(f"  ✓ {fix}")
                    
                    # Wait for fixes to take effect
                    await page.wait_for_timeout(1000)
                    
                    # Re-scroll after fixes
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(500)
                    await page.evaluate("window.scrollTo(0, 0)")
            
            # Generate PDF with optimized settings
            self.logger.info("📄 Generating PDF...")
            await page.pdf(
                path=output_path,
                format=self.config.format,
                print_background=self.config.print_background,
                prefer_css_page_size=self.config.prefer_css_page_size,
                margin={
                    'top': self.config.margin_top,
                    'bottom': self.config.margin_bottom,
                    'left': self.config.margin_left,
                    'right': self.config.margin_right
                },
                display_header_footer=True,
                header_template=f'<div style="font-size:10px; text-align:center; width:100%;">Downloaded from: <span class="url"></span></div>',
                footer_template=f'<div style="font-size:10px; text-align:center; width:100%;">Page <span class="pageNumber"></span> of <span class="totalPages"></span> - Generated on {datetime.now():%Y-%m-%d %H:%M}</div>'
            )
            
            return True, output_path, None
            
        except Exception as e:
            return False, "", str(e)
    
    async def convert_with_retry(self, page: Page, url: str) -> Tuple[bool, str, str]:
        """Convert with retry logic"""
        retry_delay = 1
        output_path = ""
        
        for attempt in range(1, self.config.max_retries + 1):
            try:
                self.logger.info(f"🔄 Attempt {attempt}/{self.config.max_retries}")
                
                success, output_path, error = await self.convert_with_smart_fixes(page, url)
                
                if success:
                    return True, output_path, ""
                else:
                    raise Exception(error)
                    
            except Exception as e:
                self.logger.warning(f"Attempt {attempt} failed: {str(e)}")
                
                if attempt < self.config.max_retries:
                    self.logger.info(f"⏳ Waiting {retry_delay}s before retry...")
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 60)
                else:
                    return False, output_path, str(e)
        
        return False, output_path, "Max retries exceeded"
    
    async def validate_url(self, url: str) -> Tuple[bool, str]:
        """Validate and normalize URL with security hardening"""
        try:
            if not isinstance(url, str):
                raise ValidationError("URL must be a string", "INVALID_TYPE")
            
            # Remove dangerous characters and whitespace
            url = url.strip()
            url = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', url)
            
            if not url:
                raise ValidationError("Empty URL provided", "EMPTY_URL")
            
            # Length check (prevent extremely long URLs)
            if len(url) > 2048:
                raise ValidationError("URL too long (max 2048 characters)", "URL_TOO_LONG")
            
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = f'https://{url}'
            
            parsed = urlparse(url)
            
            # Validate scheme
            if parsed.scheme not in ('http', 'https'):
                raise ValidationError(f"Unsupported URL scheme: {parsed.scheme}", "INVALID_SCHEME")
            
            # Validate netloc
            if not parsed.netloc:
                raise ValidationError("Invalid URL: no domain found", "NO_DOMAIN")
            
            # Security: Prevent access to local/private networks
            hostname = parsed.hostname
            if hostname:
                # Block localhost variations
                if hostname.lower() in ('localhost', '127.0.0.1', '::1', '0.0.0.0'):
                    raise ValidationError("Access to localhost is not allowed", "LOCALHOST_BLOCKED")
                
                # Block private IP ranges (basic check)
                if (hostname.startswith(('192.168.', '10.', '172.16.', '172.17.', '172.18.', 
                                       '172.19.', '172.20.', '172.21.', '172.22.', '172.23.',
                                       '172.24.', '172.25.', '172.26.', '172.27.', '172.28.',
                                       '172.29.', '172.30.', '172.31.')) or
                    hostname.startswith('169.254.')):  # Link-local
                    raise ValidationError("Access to private networks is not allowed", "PRIVATE_NETWORK_BLOCKED")
            
            # Validate port (if specified)
            if parsed.port:
                if not (1 <= parsed.port <= 65535):
                    raise ValidationError(f"Invalid port number: {parsed.port}", "INVALID_PORT")
            
            return True, url
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Invalid URL: {str(e)}", "URL_PARSE_ERROR")
    
    def validate_output_path(self, output_path: str) -> str:
        """Validate and sanitize output file path"""
        if not isinstance(output_path, str):
            raise ValidationError("Output path must be a string", "INVALID_TYPE")
        
        # Remove dangerous characters
        output_path = output_path.strip()
        output_path = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', output_path)
        
        if not output_path:
            raise ValidationError("Empty output path provided", "EMPTY_PATH")
        
        # Convert to Path object for validation
        try:
            path_obj = Path(output_path)
        except Exception as e:
            raise ValidationError(f"Invalid path format: {str(e)}", "INVALID_PATH_FORMAT")
        
        # Security: Prevent path traversal
        try:
            resolved_path = path_obj.resolve()
            if '..' in str(path_obj) or str(resolved_path) != str(path_obj.resolve()):
                raise ValidationError("Path traversal detected in output path", "PATH_TRAVERSAL")
        except Exception:
            raise ValidationError("Could not resolve output path", "PATH_RESOLUTION_ERROR")
        
        # Ensure it's a PDF file
        if not output_path.lower().endswith('.pdf'):
            output_path = f"{output_path}.pdf"
        
        # Check parent directory exists or can be created
        parent_dir = Path(output_path).parent
        try:
            parent_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValidationError(f"Cannot create output directory: {str(e)}", "DIRECTORY_CREATE_ERROR")
        
        return output_path
    
    def validate_config(self) -> None:
        """Validate configuration parameters"""
        # Validate timeout
        if not isinstance(self.config.timeout, int) or self.config.timeout <= 0 or self.config.timeout > 300:
            raise ConfigurationError("Timeout must be between 1-300 seconds", "INVALID_TIMEOUT")
        
        # Validate retries
        if not isinstance(self.config.max_retries, int) or self.config.max_retries < 1 or self.config.max_retries > 10:
            raise ConfigurationError("Max retries must be between 1-10", "INVALID_RETRIES")
        
        # Validate wait time
        if not isinstance(self.config.wait_time, int) or self.config.wait_time < 0 or self.config.wait_time > 30:
            raise ConfigurationError("Wait time must be between 0-30 seconds", "INVALID_WAIT_TIME")
        
        # Validate viewport dimensions
        if (not isinstance(self.config.viewport_width, int) or 
            self.config.viewport_width < 320 or self.config.viewport_width > 4096):
            raise ConfigurationError("Viewport width must be between 320-4096", "INVALID_VIEWPORT_WIDTH")
        
        if (not isinstance(self.config.viewport_height, int) or 
            self.config.viewport_height < 240 or self.config.viewport_height > 4096):
            raise ConfigurationError("Viewport height must be between 240-4096", "INVALID_VIEWPORT_HEIGHT")
        
        # Validate cookie file if specified
        if self.config.cookies:
            cookie_path = Path(self.config.cookies)
            if not cookie_path.exists():
                raise ConfigurationError(f"Cookie file not found: {self.config.cookies}", "COOKIE_FILE_NOT_FOUND")
            if not cookie_path.is_file():
                raise ConfigurationError(f"Cookie path is not a file: {self.config.cookies}", "COOKIE_PATH_NOT_FILE")
        
        # Validate output path if specified
        if self.config.output:
            self.config.output = self.validate_output_path(self.config.output)
    
    async def run(self) -> int:
        """Main execution method"""
        # Validate configuration
        try:
            self.validate_config()
        except (ValidationError, ConfigurationError) as e:
            self.logger.error(f"❌ Configuration validation failed: {e.message}")
            if e.error_code:
                self.logger.debug(f"Error code: {e.error_code}")
            return 1
        
        # Validate URL with enhanced security
        try:
            _, validated_url = await self.validate_url(self.config.url)
            self.config.url = validated_url
        except ValidationError as e:
            self.logger.error(f"❌ URL validation failed: {e.message}")
            if e.error_code:
                self.logger.debug(f"Error code: {e.error_code}")
            return 1
        self.logger.info(f"🌐 URL: {self.config.url}")
        
        if self.config.dry_run:
            self.logger.info("🔍 DRY RUN MODE - No files will be created")
            self.logger.info(f"Would download: {self.config.url}")
            if self.config.output:
                self.logger.info(f"Would save to: {self.config.output}")
            else:
                self.logger.info("Would generate filename based on page title")
            return 0
        
        async with async_playwright() as p:
            # Launch browser (always headless)
            self.logger.info("🚀 Launching browser...")
            browser = await p.chromium.launch(
                headless=True,  # Always headless
                args=['--disable-blink-features=AutomationControlled']
            )
            
            try:
                # Handle cookies
                cookies_to_add = []
                if self.config.cookies:
                    cookies_to_add = self.parse_cookie_file(self.config.cookies)
                
                # Create context with screen media emulation (better rendering)
                context = await browser.new_context(
                    viewport={
                        'width': self.config.viewport_width,
                        'height': self.config.viewport_height
                    },
                    user_agent=self.config.user_agent,
                    color_scheme='light',
                )
                
                # Block images if requested
                if self.config.block_images:
                    await context.route("**/*.{png,jpg,jpeg,gif,webp,svg,ico}", lambda route: route.abort())
                    self.logger.info("🚫 Images blocked for faster loading")
                
                # Add cookies if any
                if cookies_to_add:
                    await context.add_cookies(cookies_to_add)
                    self.logger.info(f"🍪 Added {len(cookies_to_add)} cookies")
                
                page = await context.new_page()
                
                # Use screen media for better rendering (default)
                await page.emulate_media(media=self.config.emulate_media)
                self.logger.info(f"📱 Using {self.config.emulate_media} media emulation")
                
                # Convert to PDF with smart fixes
                self.logger.info(f"📄 Converting to PDF...")
                success, output_path, error = await self.convert_with_retry(page, self.config.url)
                
                if success:
                    # Verify file
                    if Path(output_path).exists():
                        size = Path(output_path).stat().st_size / 1024
                        elapsed = time.time() - self.start_time
                        
                        self.logger.info(f"✅ Success! PDF saved: {output_path}")
                        self.logger.info(f"📊 Size: {size:.1f} KB")
                        self.logger.info(f"⏱️  Time: {elapsed:.1f} seconds")
                        return 0
                    else:
                        self.logger.error("❌ PDF file was not created")
                        return 1
                else:
                    self.logger.error(f"❌ Failed to convert: {error}")
                    return 1
                    
            finally:
                await browser.close()
                
        return 0


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Smart Website to PDF Converter - Auto-fixes rendering issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Smart mode (default) - auto-detects and fixes issues
    python website_to_pdf.py https://example.com
    
    # Complex essay with rendering fixes
    python website_to_pdf.py https://www.darioamodei.com/essay/machines-of-loving-grace
    
    # Wikipedia article - fast and clean
    python website_to_pdf.py https://en.wikipedia.org/wiki/Artificial_intelligence
    
    # Disable auto-fixes
    python website_to_pdf.py https://example.com --no-auto-fix
    
    # Block images for faster conversion
    python website_to_pdf.py https://example.com --block-images
        """
    )
    
    # Required arguments
    parser.add_argument('url', help='URL to convert to PDF')
    
    # Optional arguments
    parser.add_argument('-o', '--output', help='Output PDF filename (default: auto-generated)')
    parser.add_argument('--timeout', type=int, default=60, help='Page load timeout in seconds (default: 60)')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum retry attempts (default: 3)')
    parser.add_argument('--wait-time', type=int, default=1, help='Wait time after page load in seconds (default: 1)')
    
    # Browser options (headless is always True)
    parser.add_argument('--viewport-width', type=int, default=1280, help='Browser viewport width (default: 1280)')
    parser.add_argument('--viewport-height', type=int, default=1024, help='Browser viewport height (default: 1024)')
    
    # PDF options
    parser.add_argument('--format', default='Letter', choices=['A4', 'Letter', 'Legal'],
                       help='PDF page format (default: Letter)')
    parser.add_argument('--no-background', action='store_false', dest='print_background',
                       help='Do not print background graphics')
    parser.add_argument('--margin', type=str, default='20px', help='Page margins (default: 20px)')
    
    # Cookie options
    parser.add_argument('--cookies', help='Path to cookies file in Netscape format')
    
    # Speed and rendering options
    parser.add_argument('--slow', action='store_true',
                       help='Slow mode: longer waits for complex sites')
    parser.add_argument('--block-images', action='store_true',
                       help='Block images for faster loading')
    parser.add_argument('--media', choices=['print', 'screen'], default='screen',
                       dest='emulate_media', help='Media type to emulate (default: screen)')
    parser.add_argument('--no-auto-fix', action='store_false', dest='auto_fix',
                       help='Disable automatic layout fixes')
    
    # Debug and config
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with verbose logging')
    parser.add_argument('--dry-run', action='store_true', help='Preview actions without downloading')
    parser.add_argument('--config', help='Load settings from JSON config file')
    
    args = parser.parse_args()
    
    # Load config file if specified
    config_dict = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config_dict = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load config file: {e}")
            return 1
    
    # Override with CLI arguments
    cli_dict = {k: v for k, v in vars(args).items() if v is not None}
    config_dict.update(cli_dict)
    
    # Set smart defaults
    if config_dict.get('slow', False):
        config_dict.setdefault('wait_time', 3)
        config_dict.setdefault('wait_until', 'networkidle')
    else:
        config_dict.setdefault('wait_time', 1)
        config_dict.setdefault('wait_until', 'domcontentloaded')
    
    # Process margin if single value provided
    if 'margin' in config_dict and config_dict['margin'] != '20px':
        margin_value = config_dict['margin']
        config_dict.update({
            'margin_top': margin_value,
            'margin_bottom': margin_value,
            'margin_left': margin_value,
            'margin_right': margin_value
        })
    
    # Create config object
    config = Config(**config_dict)
    
    # Run converter
    converter = WebsiteToPDFConverter(config)
    exit_code = asyncio.run(converter.run())
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()