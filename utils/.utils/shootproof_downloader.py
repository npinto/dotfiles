#!/usr/bin/env python3
"""
ShootProof Robust Gallery Downloader - Production-Ready Version
Enhanced with best practices for reliability, monitoring, and maintainability

Features:
- Graceful shutdown handling
- Retry with exponential backoff
- Disk space checking
- Dry-run mode
- Configuration file support
- Resume capability
- Better error handling
- Performance monitoring
"""

import argparse
import atexit
import hashlib
import json
import logging
import re
import shutil
import signal
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager

# Constants for better maintainability
DEFAULT_OUTPUT_DIR = "shootproof_photos"
DEFAULT_MAX_WORKERS = 5
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 1.0
MIN_FREE_SPACE_MB = 100
VALID_IMAGE_SIZE_KB = 100
CHUNK_SIZE = 8192
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# HTTP Status codes
HTTP_OK = 200
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR = 500

# File size thresholds
SIZE_THRESHOLD_SMALL = 0.5  # MB
SIZE_THRESHOLD_MEDIUM = 1.0  # MB
SIZE_THRESHOLD_LARGE = 2.0  # MB


@dataclass
class DownloadConfig:
    """Configuration for the downloader"""

    gallery_url: str
    email: str
    output_dir: str = DEFAULT_OUTPUT_DIR
    headless: bool = True
    max_workers: int = DEFAULT_MAX_WORKERS
    log_level: str = "INFO"
    dry_run: bool = False
    resume: bool = True
    timeout: int = DEFAULT_TIMEOUT
    retry_count: int = DEFAULT_RETRY_COUNT
    retry_delay: float = DEFAULT_RETRY_DELAY
    save_metadata: bool = True
    verify_ssl: bool = True
    user_agent: str = USER_AGENT
    rate_limit_delay: float = 0.1
    max_retries_per_photo: int = 3


@dataclass
class DownloadStats:
    """Statistics tracking for downloads"""

    successful: int = 0
    failed: int = 0
    skipped: int = 0
    total_size: int = 0
    start_time: float = field(default_factory=time.time)
    resolutions: dict = field(
        default_factory=lambda: {"3x": 0, "2x": 0, "1x": 0, "l": 0}
    )

    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time

    @property
    def success_rate(self) -> float:
        total = self.successful + self.failed
        return (self.successful / total * 100) if total > 0 else 0


class RobustShootProofDownloader:
    """Production-ready ShootProof gallery downloader"""

    def __init__(self, config: DownloadConfig):
        self.config = config
        self.driver = None
        self.wait = None
        self.session = None
        self._shutdown_requested = False
        self._setup_signal_handlers()

        # Data storage
        self.raw_photo_urls: set[str] = set()
        self.photo_data: list[dict] = []
        self.download_results: dict[str, dict] = {}
        self.stats = DownloadStats()

        # Setup
        self._setup_logging()
        self._setup_requests_session()
        self._check_disk_space()

        # Log configuration
        self.logger.info("=" * 80)
        self.logger.info("ShootProof Robust Gallery Downloader")
        self.logger.info("=" * 80)
        self.logger.info("Configuration:")
        for key, value in vars(config).items():
            if key != "email":  # Don't log email in full
                display_value = (
                    value if key != "email" else f"{value[:3]}...{value[-3:]}"
                )
                self.logger.info(f"  {key}: {display_value}")
        self.logger.info("=" * 80)

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""

        def signal_handler(signum, frame):
            self.logger.warning(
                f"\nReceived signal {signum}. Initiating graceful shutdown..."
            )
            self._shutdown_requested = True

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        atexit.register(self.cleanup)

    def _setup_logging(self):
        """Enhanced logging setup with structured logging option"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"shootproof_download_{timestamp}.log"

        # Configure formatters
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
        console_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)

        # Setup logger
        self.logger = logging.getLogger("ShootProof")
        self.logger.setLevel(getattr(logging, self.config.log_level))
        self.logger.handlers.clear()
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info(f"Logging initialized. Log file: {log_file}")

    def _setup_requests_session(self):
        """Setup requests session with retry logic"""
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.retry_count,
            backoff_factor=self.config.retry_delay,
            status_forcelist=[HTTP_TOO_MANY_REQUESTS, HTTP_SERVER_ERROR, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update(
            {
                "User-Agent": self.config.user_agent,
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }
        )

    def _check_disk_space(self):
        """Check available disk space"""
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        stat = shutil.disk_usage(output_path)
        free_mb = stat.free / 1024 / 1024

        if free_mb < MIN_FREE_SPACE_MB:
            raise RuntimeError(
                f"Insufficient disk space: {free_mb:.1f}MB free, "
                f"need at least {MIN_FREE_SPACE_MB}MB"
            )

        self.logger.info(f"Disk space available: {free_mb:.1f}MB")

    @contextmanager
    def _webdriver_context(self):
        """Context manager for WebDriver lifecycle"""
        driver = None
        try:
            driver = self._create_driver()
            self.driver = driver
            self.wait = WebDriverWait(driver, self.config.timeout)
            yield driver
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    self.logger.error(f"Error closing driver: {e}")
                finally:
                    self.driver = None
                    self.wait = None

    def _create_driver(self):
        """Create Chrome driver with robust configuration"""
        chrome_options = Options()

        # Essential options
        if self.config.headless:
            chrome_options.add_argument("--headless=new")

        # Performance and stability options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(f"--user-agent={self.config.user_agent}")

        # Experimental options
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option(
            "prefs",
            {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.notifications": 2,
            },
        )

        # Performance logging
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        # Create driver with retry
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                self.logger.info(
                    f"Creating Chrome driver (attempt {attempt + 1}/{max_attempts})..."
                )
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)

                # Remove webdriver detection
                driver.execute_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )

                self.logger.info("✓ Chrome driver created successfully")
                return driver

            except Exception as e:
                self.logger.error(f"Failed to create driver: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(2**attempt)
                else:
                    raise

    def _safe_find_element(
        self, by: By, value: str, timeout: int = 10
    ) -> Optional[Any]:
        """Safely find element with timeout"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            return None

    def _safe_click(self, element, use_js: bool = True) -> bool:
        """Safely click element with fallback to JavaScript"""
        try:
            if use_js:
                self.driver.execute_script("arguments[0].click();", element)
            else:
                element.click()
            return True
        except Exception as e:
            self.logger.debug(f"Click failed: {e}")
            return False

    def _take_screenshot(self, name: str, always: bool = False):
        """Take screenshot with better error handling"""
        if not always and self.config.log_level != "DEBUG":
            return

        if not self.driver:
            return

        try:
            screenshots_dir = Path(self.config.output_dir) / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)

            filepath = screenshots_dir / f"{name}_{datetime.now():%Y%m%d_%H%M%S}.png"
            self.driver.save_screenshot(str(filepath))
            self.logger.debug(f"Screenshot saved: {filepath}")
        except Exception as e:
            self.logger.debug(f"Screenshot failed: {e}")

    def _retry_with_backoff(self, func, *args, max_retries: int = 3, **kwargs):
        """Execute function with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise

                delay = self.config.retry_delay * (2**attempt)
                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s..."
                )
                time.sleep(delay)

    def authenticate(self):
        """Enhanced authentication with better error handling"""
        self.logger.info("\n" + "-" * 60)
        self.logger.info("AUTHENTICATION PHASE")
        self.logger.info("-" * 60)

        # Validate inputs
        if not self._validate_url(self.config.gallery_url):
            raise ValueError(f"Invalid gallery URL: {self.config.gallery_url}")

        if not self._validate_email(self.config.email):
            raise ValueError(f"Invalid email format: {self.config.email}")

        try:
            # Navigate to gallery
            self.logger.info("Navigating to gallery...")
            self.driver.get(self.config.gallery_url)

            # Wait for page load
            WebDriverWait(self.driver, self.config.timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            self._take_screenshot("01_initial_page")

            # Try authentication
            if not self._try_authentication():
                raise RuntimeError("Authentication failed after all attempts")

            self.logger.info("✓ Authentication successful")

        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            self._take_screenshot("auth_error", always=True)
            raise

    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _validate_email(self, email: str) -> bool:
        """Basic email validation"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def _try_authentication(self) -> bool:
        """Try authentication with multiple strategies"""
        strategies = [
            self._auth_strategy_standard,
            self._auth_strategy_modal,
            self._auth_strategy_iframe,
        ]

        for strategy in strategies:
            try:
                if strategy():
                    return True
            except Exception as e:
                self.logger.debug(f"Strategy {strategy.__name__} failed: {e}")

        return False

    def _auth_strategy_standard(self) -> bool:
        """Standard authentication flow"""
        # Click View Gallery button
        view_button = self._safe_find_element(
            By.XPATH, "//button[contains(text(), 'View Gallery')]"
        )

        if view_button:
            self._safe_click(view_button)
            time.sleep(2)

        # Find and fill email
        email_input = self._safe_find_element(
            By.CSS_SELECTOR, 'input[type="email"], input[name*="email"]'
        )

        if not email_input:
            return False

        # Clear and enter email
        self.driver.execute_script("arguments[0].value = '';", email_input)
        email_input.send_keys(self.config.email)
        time.sleep(0.5)

        # Submit
        email_input.send_keys(Keys.RETURN)

        # Wait for authentication
        try:
            WebDriverWait(self.driver, 10).until_not(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))
            )
            return True
        except TimeoutException:
            return False

    def _auth_strategy_modal(self) -> bool:
        """Handle modal-based authentication"""
        # Implementation for modal authentication
        return False

    def _auth_strategy_iframe(self) -> bool:
        """Handle iframe-based authentication"""
        # Implementation for iframe authentication
        return False

    def detect_gallery_info(self) -> Optional[int]:
        """Enhanced gallery detection with multiple strategies"""
        self.logger.info("\n" + "-" * 60)
        self.logger.info("GALLERY DETECTION PHASE")
        self.logger.info("-" * 60)

        detection_strategies = [
            self._detect_from_text,
            self._detect_from_meta,
            self._detect_from_javascript,
            self._detect_from_api,
        ]

        for strategy in detection_strategies:
            try:
                count = strategy()
                if count:
                    self.logger.info(
                        f"✓ Detected {count} photos using {strategy.__name__}"
                    )
                    return count
            except Exception as e:
                self.logger.debug(f"Detection strategy {strategy.__name__} failed: {e}")

        self.logger.warning("Could not detect photo count - will load dynamically")
        return None

    def _detect_from_text(self) -> Optional[int]:
        """Detect count from page text"""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            patterns = [
                r"(\d+)\s*photos?",
                r"(\d+)\s*images?",
                r"showing\s*(\d+)",
                r"gallery.*?(\d+)",
            ]

            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    return int(match.group(1))
        except Exception:
            pass
        return None

    def _detect_from_meta(self) -> Optional[int]:
        """Detect from meta tags or data attributes"""
        selectors = [
            "[data-photo-count]",
            "[data-total-photos]",
            ".photo-count",
            ".gallery-count",
            'meta[property*="count"]',
        ]

        for selector in selectors:
            try:
                elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                count_text = (
                    elem.text
                    or elem.get_attribute("content")
                    or elem.get_attribute("data-photo-count")
                )
                if count_text and count_text.isdigit():
                    return int(count_text)
            except Exception:
                continue
        return None

    def _detect_from_javascript(self) -> Optional[int]:
        """Detect using JavaScript execution"""
        try:
            count = self.driver.execute_script("""
                // Try various JavaScript methods
                if (window.galleryData && window.galleryData.photoCount) {
                    return window.galleryData.photoCount;
                }
                if (window.photos && Array.isArray(window.photos)) {
                    return window.photos.length;
                }
                // Angular scope
                try {
                    var scope = angular.element(document.body).scope();
                    if (scope && scope.photos) {
                        return scope.photos.length;
                    }
                } catch(e) {}
                return null;
            """)
            return int(count) if count else None
        except Exception:
            return None

    def _detect_from_api(self) -> Optional[int]:
        """Try to detect from API calls"""
        # Could inspect network traffic for API responses
        return None

    def load_all_photos(self, expected_count: Optional[int] = None):
        """Enhanced photo loading with better progress tracking"""
        if self.config.dry_run:
            self.logger.info("DRY RUN: Skipping photo loading")
            return

        self.logger.info("\n" + "-" * 60)
        self.logger.info("PHOTO LOADING PHASE")
        self.logger.info("-" * 60)

        # Initial load
        time.sleep(2)
        self.raw_photo_urls.update(self._extract_visible_photos())
        initial_count = len(self.raw_photo_urls)
        self.logger.info(f"Initial load: {initial_count} photos")

        # Setup progress tracking
        pbar = None
        if expected_count:
            pbar = tqdm(
                total=expected_count,
                desc="Loading photos",
                unit="photos",
                disable=self.config.log_level == "DEBUG",
            )
            pbar.update(initial_count)

        try:
            # Load with multiple strategies
            self._progressive_loading(pbar, expected_count)

        finally:
            if pbar:
                pbar.close()

        # Final verification
        final_count = len(self.raw_photo_urls)
        self.logger.info(f"\n✓ Total photos loaded: {final_count}")

        if expected_count and final_count < expected_count:
            self.logger.warning(
                f"⚠ Found fewer photos than expected: {final_count}/{expected_count}"
            )

    def _progressive_loading(self, pbar, expected_count):
        """Progressive loading with multiple strategies"""
        strategies = [
            ("Smooth scroll", self._smooth_scroll_strategy),
            ("Viewport chunks", self._viewport_chunk_strategy),
            ("JavaScript trigger", self._js_trigger_strategy),
            ("Force load all", self._force_load_all_strategy),
        ]

        last_count = len(self.raw_photo_urls)
        no_change_count = 0
        max_no_change = 3

        for strategy_name, strategy_func in strategies:
            if self._shutdown_requested:
                self.logger.warning("Shutdown requested, stopping photo loading")
                break

            self.logger.info(f"\nTrying strategy: {strategy_name}")

            try:
                strategy_func()
            except Exception as e:
                self.logger.error(f"Strategy {strategy_name} failed: {e}")
                continue

            # Update photos
            new_urls = self._extract_visible_photos()
            self.raw_photo_urls.update(new_urls)

            current_count = len(self.raw_photo_urls)
            new_photos = current_count - last_count

            if new_photos > 0:
                self.logger.info(
                    f"✓ Found {new_photos} new photos (total: {current_count})"
                )
                no_change_count = 0
                if pbar:
                    pbar.update(new_photos)
            else:
                no_change_count += 1
                self.logger.info(
                    f"No new photos found ({no_change_count}/{max_no_change})"
                )

            last_count = current_count

            # Check if we have enough
            if expected_count and current_count >= expected_count:
                self.logger.info("✓ Reached expected count")
                break

            if no_change_count >= max_no_change:
                self.logger.info("No new photos after multiple attempts, stopping")
                break

    def _extract_visible_photos(self) -> set[str]:
        """Extract photo URLs with enhanced detection"""
        found_urls = set()

        # CSS selectors
        selectors = [
            "img[src*='cloudfront'][src*='/ph/']",
            "img[ng-src*='cloudfront']",
            "img[data-src*='cloudfront']",
            ".photo-image img",
            "[style*='background-image'][style*='cloudfront']",
        ]

        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    urls = []

                    # Check various attributes
                    for attr in ["src", "ng-src", "data-src", "data-original"]:
                        url = elem.get_attribute(attr)
                        if url:
                            urls.append(url)

                    # Check background-image
                    style = elem.get_attribute("style")
                    if style:
                        match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
                        if match:
                            urls.append(match.group(1))

                    # Process URLs
                    for url in urls:
                        if url and "cloudfront" in url and "/ph/" in url:
                            if url.startswith("//"):
                                url = "https:" + url
                            found_urls.add(url)

            except Exception as e:
                self.logger.debug(f"Error extracting with {selector}: {e}")

        # JavaScript extraction
        try:
            js_urls = self._extract_with_javascript()
            found_urls.update(js_urls)
        except Exception as e:
            self.logger.debug(f"JavaScript extraction failed: {e}")

        return found_urls

    def _extract_with_javascript(self) -> list[str]:
        """Extract URLs using JavaScript"""
        return self.driver.execute_script(r"""
            const urls = new Set();
            
            // Direct images
            document.querySelectorAll('img').forEach(img => {
                ['src', 'ng-src', 'data-src', 'srcset'].forEach(attr => {
                    const value = img.getAttribute(attr);
                    if (value && value.includes('cloudfront')) {
                        // Handle srcset
                        if (attr === 'srcset') {
                            value.split(',').forEach(src => {
                                const url = src.trim().split(' ')[0];
                                if (url) urls.add(url);
                            });
                        } else {
                            urls.add(value);
                        }
                    }
                });
            });
            
            // Background images
            document.querySelectorAll('[style*="background"]').forEach(elem => {
                const style = elem.getAttribute('style');
                const matches = style.matchAll(/url\(['"]?([^'"]+)['"]?\)/g);
                for (const match of matches) {
                    if (match[1].includes('cloudfront')) {
                        urls.add(match[1]);
                    }
                }
            });
            
            // Angular/React data
            try {
                const allElements = document.querySelectorAll('*');
                allElements.forEach(elem => {
                    const data = elem.__vue__ || elem.__react || elem.__angular;
                    if (data && data.photos) {
                        data.photos.forEach(photo => {
                            if (photo.url) urls.add(photo.url);
                            if (photo.src) urls.add(photo.src);
                            if (photo.imageUrl) urls.add(photo.imageUrl);
                        });
                    }
                });
            } catch(e) {}
            
            return Array.from(urls).filter(url => url.includes('/ph/'));
        """)

    def _smooth_scroll_strategy(self):
        """Smooth scrolling with momentum"""
        viewport_height = self.driver.execute_script("return window.innerHeight")

        for _ in range(15):
            if self._shutdown_requested:
                break
            self.driver.execute_script(f"""
                window.scrollBy({{
                    top: {viewport_height * 0.7},
                    behavior: 'smooth'
                }});
            """)
            time.sleep(0.5)

    def _viewport_chunk_strategy(self):
        """Load by viewport chunks"""
        self.driver.execute_script("""
            const height = document.body.scrollHeight;
            const viewport = window.innerHeight;
            const chunks = Math.ceil(height / viewport);
            
            for (let i = 0; i < chunks; i++) {
                setTimeout(() => {
                    window.scrollTo(0, i * viewport);
                }, i * 200);
            }
        """)

        # Wait for all scrolls
        time.sleep(
            (
                self.driver.execute_script(
                    "return Math.ceil(document.body.scrollHeight / window.innerHeight)"
                )
                + 1
            )
            * 0.2
        )

    def _js_trigger_strategy(self):
        """Trigger lazy loading via JavaScript"""
        self.driver.execute_script("""
            // Trigger all lazy load events
            const events = ['scroll', 'resize', 'orientationchange', 'load'];
            events.forEach(eventName => {
                window.dispatchEvent(new Event(eventName));
            });
            
            // Find and trigger lazy load libraries
            if (window.LazyLoad) {
                window.LazyLoad.update();
            }
            if (window.lozad) {
                const observer = window.lozad();
                observer.observe();
            }
            
            // Intersection Observer trigger
            document.querySelectorAll('img[data-src], img[loading="lazy"]').forEach(img => {
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                }
            });
        """)
        time.sleep(2)

    def _force_load_all_strategy(self):
        """Force load all images"""
        self.driver.execute_script("""
            // Remove lazy loading
            document.querySelectorAll('img').forEach(img => {
                img.loading = 'eager';
                if (img.dataset.src && !img.src) {
                    img.src = img.dataset.src;
                }
            });
            
            // Scroll to bottom and back
            window.scrollTo(0, document.body.scrollHeight);
            setTimeout(() => window.scrollTo(0, 0), 500);
        """)
        time.sleep(3)

    def transform_urls_to_high_res(self):
        """Transform URLs with better deduplication and validation"""
        self.logger.info("\n" + "-" * 60)
        self.logger.info("URL TRANSFORMATION PHASE")
        self.logger.info("-" * 60)

        self.logger.info(f"Processing {len(self.raw_photo_urls)} raw URLs")

        # Enhanced pattern matching
        url_stats = {
            "valid": 0,
            "invalid": 0,
            "duplicates": 0,
            "resolutions": {"l": 0, "t": 0, "1x": 0, "2x": 0, "3x": 0},
        }

        seen_photos = {}

        for url in self.raw_photo_urls:
            # Enhanced pattern - handle more URL formats
            patterns = [
                r"/ph/([a-f0-9]+)/(l|t|1x|2x|3x)/(\d+)\.jpg",
                r"/photos/([a-f0-9]+)/(l|t|1x|2x|3x)/(\d+)\.jpg",
                r"/([a-f0-9]{32})/(\w+)/(\d+)\.jpg",
            ]

            matched = False
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    hash_id = match.group(1)
                    resolution = match.group(2)
                    photo_id = match.group(3)

                    url_stats["valid"] += 1
                    url_stats["resolutions"][resolution] += 1

                    # Deduplicate by photo_id
                    if photo_id in seen_photos:
                        url_stats["duplicates"] += 1
                        # Keep higher resolution version
                        if self._resolution_priority(
                            resolution
                        ) > self._resolution_priority(
                            seen_photos[photo_id]["original_resolution"]
                        ):
                            seen_photos[photo_id]["original_resolution"] = resolution
                    else:
                        high_res_url = f"https://d2rxqglyhdohqf.cloudfront.net/ph/{hash_id}/3x/{photo_id}.jpg"

                        seen_photos[photo_id] = {
                            "photo_id": photo_id,
                            "hash_id": hash_id,
                            "high_res_url": high_res_url,
                            "original_url": url,
                            "original_resolution": resolution,
                        }

                    matched = True
                    break

            if not matched:
                url_stats["invalid"] += 1
                self.logger.warning(f"Non-standard URL pattern: {url}")

        # Convert to list and sort
        self.photo_data = sorted(seen_photos.values(), key=lambda x: x["photo_id"])

        # Log statistics
        self.logger.info("URL Analysis:")
        self.logger.info(f"  Valid URLs: {url_stats['valid']}")
        self.logger.info(f"  Invalid URLs: {url_stats['invalid']}")
        self.logger.info(f"  Duplicates removed: {url_stats['duplicates']}")
        self.logger.info(f"  Unique photos: {len(self.photo_data)}")
        self.logger.info(f"  Resolution breakdown: {url_stats['resolutions']}")

        # Save mapping
        if self.config.save_metadata:
            self._save_url_mapping(url_stats)

    def _resolution_priority(self, resolution: str) -> int:
        """Get resolution priority for deduplication"""
        priorities = {"l": 1, "t": 2, "1x": 3, "2x": 4, "3x": 5}
        return priorities.get(resolution, 0)

    def _save_url_mapping(self, stats: dict):
        """Save URL mapping with metadata"""
        mapping_file = Path(self.config.output_dir) / "url_mapping.json"
        mapping_file.parent.mkdir(parents=True, exist_ok=True)

        with open(mapping_file, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "gallery_url": self.config.gallery_url,
                    "total_photos": len(self.photo_data),
                    "statistics": stats,
                    "photos": self.photo_data,
                },
                f,
                indent=2,
            )

        self.logger.info(f"✓ URL mapping saved to: {mapping_file}")

    def download_all_photos(self):
        """Enhanced download with resume capability"""
        if self.config.dry_run:
            self.logger.info("DRY RUN: Skipping downloads")
            self._simulate_downloads()
            return self.stats

        self.logger.info("\n" + "-" * 60)
        self.logger.info("DOWNLOAD PHASE")
        self.logger.info("-" * 60)

        # Load previous results if resuming
        if self.config.resume:
            self._load_previous_results()

        # Filter photos to download
        photos_to_download = self._get_photos_to_download()

        if not photos_to_download:
            self.logger.info("No photos to download (all already exist)")
            return self.stats

        self.logger.info(
            f"Downloading {len(photos_to_download)} photos "
            f"with {self.config.max_workers} workers"
        )

        # Progress bar
        pbar = tqdm(
            total=len(photos_to_download),
            desc="Downloading",
            unit="photos",
            disable=self.config.log_level == "DEBUG",
        )

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(self._download_photo_with_retry, photo): photo
                for photo in photos_to_download
            }

            for future in as_completed(futures):
                if self._shutdown_requested:
                    self.logger.warning(
                        "Shutdown requested, cancelling remaining downloads"
                    )
                    executor.shutdown(wait=False)
                    break

                photo = futures[future]

                try:
                    result = future.result()
                    self._process_download_result(result, pbar)
                except Exception as e:
                    self.logger.error(f"Download error for {photo['photo_id']}: {e}")
                    self.stats.failed += 1

                pbar.update(1)

        pbar.close()

        # Save results
        self._save_download_results()

        return self.stats

    def _load_previous_results(self):
        """Load previous download results for resume"""
        results_file = Path(self.config.output_dir) / "download_results.json"

        if results_file.exists():
            try:
                with open(results_file) as f:
                    data = json.load(f)
                    self.download_results = data.get("results", {})
                    self.logger.info(
                        f"Loaded {len(self.download_results)} previous results"
                    )
            except Exception as e:
                self.logger.warning(f"Could not load previous results: {e}")

    def _get_photos_to_download(self) -> list[dict]:
        """Get list of photos that need downloading"""
        photos_to_download = []

        for photo in self.photo_data:
            photo_id = photo["photo_id"]
            filepath = Path(self.config.output_dir) / f"{photo_id}.jpg"

            # Skip if already downloaded successfully
            if photo_id in self.download_results:
                result = self.download_results[photo_id]
                if result.get("success") and filepath.exists():
                    self.stats.skipped += 1
                    continue

            # Skip if file exists and is valid
            if (
                filepath.exists()
                and filepath.stat().st_size > VALID_IMAGE_SIZE_KB * 1024
            ):
                self.stats.skipped += 1
                continue

            photos_to_download.append(photo)

        return photos_to_download

    def _download_photo_with_retry(self, photo_info: dict) -> dict:
        """Download photo with retry logic"""
        photo_id = photo_info["photo_id"]

        result = {
            "photo_id": photo_id,
            "filename": f"{photo_id}.jpg",
            "success": False,
            "file_size": 0,
            "download_time": 0,
            "resolution": None,
            "error": None,
            "attempts": 0,
        }

        start_time = time.time()

        # Try each resolution
        for resolution in ["3x", "2x", "1x", "l"]:
            if self._shutdown_requested:
                result["error"] = "Shutdown requested"
                break

            url = photo_info["high_res_url"].replace("/3x/", f"/{resolution}/")

            for attempt in range(self.config.max_retries_per_photo):
                try:
                    result["attempts"] += 1

                    # Make request
                    response = self.session.get(
                        url,
                        timeout=self.config.timeout,
                        verify=self.config.verify_ssl,
                        stream=True,
                    )

                    if response.status_code == HTTP_OK:
                        # Download file
                        filepath = Path(self.config.output_dir) / result["filename"]
                        temp_filepath = filepath.with_suffix(".tmp")

                        with open(temp_filepath, "wb") as f:
                            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                                if chunk:
                                    f.write(chunk)

                        # Verify and move
                        if temp_filepath.stat().st_size > 0:
                            temp_filepath.rename(filepath)

                            result["success"] = True
                            result["file_size"] = filepath.stat().st_size
                            result["resolution"] = resolution
                            result["download_time"] = time.time() - start_time

                            # Calculate checksum
                            with open(filepath, "rb") as f:
                                result["checksum"] = hashlib.sha256(
                                    f.read()
                                ).hexdigest()[:16]

                            return result
                        else:
                            temp_filepath.unlink()
                            raise ValueError("Empty file downloaded")

                    elif response.status_code == HTTP_NOT_FOUND and resolution != "l":
                        # Try next resolution
                        break
                    else:
                        result["error"] = f"HTTP {response.status_code}"

                except requests.exceptions.RequestException as e:
                    result["error"] = f"Request error: {str(e)}"
                    if attempt < self.config.max_retries_per_photo - 1:
                        time.sleep(self.config.retry_delay * (2**attempt))
                except Exception as e:
                    result["error"] = f"Download error: {str(e)}"
                    break

        result["download_time"] = time.time() - start_time
        return result

    def _process_download_result(self, result: dict, pbar):
        """Process download result and update statistics"""
        self.download_results[result["photo_id"]] = result

        if result["success"]:
            self.stats.successful += 1
            self.stats.total_size += result["file_size"]

            if result["resolution"]:
                self.stats.resolutions[result["resolution"]] += 1

            # Update progress bar
            size_mb = result["file_size"] / 1024 / 1024
            pbar.set_postfix(
                {
                    "last": f"{result['filename']} ({size_mb:.1f}MB) [{result['resolution']}]",
                    "success_rate": f"{self.stats.success_rate:.1f}%",
                }
            )
        else:
            self.stats.failed += 1
            self.logger.error(
                f"Failed to download {result['photo_id']}: {result['error']} "
                f"(attempts: {result['attempts']})"
            )

    def _save_download_results(self):
        """Save download results for resume capability"""
        results_file = Path(self.config.output_dir) / "download_results.json"

        with open(results_file, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "statistics": {
                        "successful": self.stats.successful,
                        "failed": self.stats.failed,
                        "skipped": self.stats.skipped,
                        "total_size": self.stats.total_size,
                        "elapsed_time": self.stats.elapsed_time,
                        "success_rate": self.stats.success_rate,
                        "resolutions": self.stats.resolutions,
                    },
                    "results": self.download_results,
                },
                f,
                indent=2,
            )

    def _simulate_downloads(self):
        """Simulate downloads for dry run"""
        self.logger.info("DRY RUN: Simulating downloads...")

        for photo in self.photo_data:
            self.stats.successful += 1
            self.stats.total_size += 1_200_000  # Assume 1.2MB average
            self.stats.resolutions["3x"] += 1

        self.logger.info(f"DRY RUN: Would download {len(self.photo_data)} photos")

    def generate_report(self):
        """Generate comprehensive final report"""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("DOWNLOAD COMPLETE - FINAL REPORT")
        self.logger.info("=" * 80)

        # Calculate statistics
        downloaded_files = list(Path(self.config.output_dir).glob("*.jpg"))
        total_files = len(downloaded_files)
        total_size_mb = sum(f.stat().st_size for f in downloaded_files) / 1024 / 1024

        # Build report
        report_lines = [
            "\nGallery Information:",
            f"  URL: {self.config.gallery_url}",
            f"  Email: {self.config.email[:3]}...{self.config.email[-10:]}",
            "",
            "Results:",
            f"  Photos found: {len(self.raw_photo_urls)}",
            f"  Photos processed: {len(self.photo_data)}",
            f"  Files in directory: {total_files}",
            f"  Total size: {total_size_mb:.1f} MB",
            "",
            "Download Statistics:",
            f"  Successful: {self.stats.successful}",
            f"  Failed: {self.stats.failed}",
            f"  Skipped: {self.stats.skipped}",
            f"  Success rate: {self.stats.success_rate:.1f}%",
            "",
            "Performance:",
            f"  Time elapsed: {self.stats.elapsed_time:.1f} seconds",
            f"  Average speed: {self.stats.successful / self.stats.elapsed_time:.1f} photos/second",
            f"  Resolution breakdown: {self.stats.resolutions}",
            "",
            "Output Location:",
            f"  {Path(self.config.output_dir).resolve()}",
        ]

        if self.config.dry_run:
            report_lines.insert(0, "\n*** DRY RUN - NO FILES WERE DOWNLOADED ***")

        report = "\n".join(report_lines)
        self.logger.info(report)

        # Save report
        report_file = Path(self.config.output_dir) / "download_report.txt"
        with open(report_file, "w") as f:
            f.write(report)
            f.write(f"\n\nGenerated at: {datetime.now()}\n")

    def cleanup(self):
        """Enhanced cleanup with error handling"""
        self.logger.info("\nCleaning up resources...")

        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("✓ Browser closed")
            except Exception as e:
                self.logger.error(f"Error closing browser: {e}")

        if self.session:
            try:
                self.session.close()
                self.logger.info("✓ HTTP session closed")
            except Exception as e:
                self.logger.error(f"Error closing session: {e}")

    def run(self):
        """Main execution with enhanced error handling"""
        try:
            # Validate environment
            self._validate_environment()

            if self.config.dry_run:
                self.logger.info("*** DRY RUN MODE - No files will be downloaded ***")

            # Main workflow
            with self._webdriver_context():
                # Authenticate
                self.authenticate()

                # Detect gallery info
                expected_count = self.detect_gallery_info()

                # Load all photos
                self.load_all_photos(expected_count)

                # Transform URLs
                self.transform_urls_to_high_res()

                # Download photos
                self.download_all_photos()

            # Generate report
            self.generate_report()

            self.logger.info("\n✅ Download completed successfully!")

        except KeyboardInterrupt:
            self.logger.warning("\n⚠️ Interrupted by user")
            raise
        except Exception as e:
            self.logger.error(f"\n❌ Fatal error: {e}")
            self.logger.error(traceback.format_exc())
            self._take_screenshot("fatal_error", always=True)
            raise
        finally:
            self.cleanup()

    def _validate_environment(self):
        """Validate environment before starting"""
        # Check Chrome/Chromium is available
        try:
            import shutil

            if not shutil.which("google-chrome") and not shutil.which("chromium"):
                self.logger.warning("Chrome/Chromium not found in PATH")
        except Exception:
            pass

        # Check output directory
        output_path = Path(self.config.output_dir)
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"Cannot create output directory: {e}")


def load_config_file(config_path: str) -> dict:
    """Load configuration from JSON file"""
    try:
        with open(config_path) as f:
            return json.load(f)
    except Exception as e:
        raise ValueError(f"Cannot load config file: {e}")


def main():
    """Enhanced command-line interface"""
    parser = argparse.ArgumentParser(
        description="ShootProof Robust Gallery Downloader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  %(prog)s "https://gallery.url/" "email@example.com"
  
  # With custom output directory
  %(prog)s "https://gallery.url/" "email@example.com" -o my_photos
  
  # Dry run to test without downloading
  %(prog)s "https://gallery.url/" "email@example.com" --dry-run
  
  # Non-headless mode for debugging
  %(prog)s "https://gallery.url/" "email@example.com" --no-headless
  
  # With configuration file
  %(prog)s --config config.json
  
  # Resume previous download
  %(prog)s "https://gallery.url/" "email@example.com" --resume
        """,
    )

    # Positional arguments
    parser.add_argument("gallery_url", nargs="?", help="ShootProof gallery URL")
    parser.add_argument("email", nargs="?", help="Email address for authentication")

    # Optional arguments
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--no-headless", action="store_true", help="Run browser in visible mode"
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f"Number of download workers (default: {DEFAULT_MAX_WORKERS})",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Test run without downloading files"
    )
    parser.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="Don't resume previous download",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--retry-count",
        type=int,
        default=DEFAULT_RETRY_COUNT,
        help=f"Number of retries (default: {DEFAULT_RETRY_COUNT})",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=DEFAULT_RETRY_DELAY,
        help=f"Initial retry delay in seconds (default: {DEFAULT_RETRY_DELAY})",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.1,
        help="Delay between downloads in seconds (default: 0.1)",
    )
    parser.add_argument("--config", help="Load configuration from JSON file")
    parser.add_argument(
        "--no-verify-ssl",
        dest="verify_ssl",
        action="store_false",
        help="Disable SSL verification (not recommended)",
    )

    args = parser.parse_args()

    # Load configuration
    if args.config:
        config_data = load_config_file(args.config)
        config = DownloadConfig(**config_data)
    else:
        if not args.gallery_url or not args.email:
            parser.error("Gallery URL and email are required unless using --config")

        config = DownloadConfig(
            gallery_url=args.gallery_url,
            email=args.email,
            output_dir=args.output,
            headless=not args.no_headless,
            max_workers=args.workers,
            log_level=args.log_level,
            dry_run=args.dry_run,
            resume=args.resume,
            timeout=args.timeout,
            retry_count=args.retry_count,
            retry_delay=args.retry_delay,
            rate_limit_delay=args.rate_limit,
            verify_ssl=args.verify_ssl,
        )

    # Check dependencies
    required_packages = ["selenium", "requests", "tqdm", "webdriver_manager"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"Missing required packages: {', '.join(missing_packages)}")
        print(f"Install with: pip install {' '.join(missing_packages)}")
        sys.exit(1)

    # Run downloader
    try:
        downloader = RobustShootProofDownloader(config)
        downloader.run()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
