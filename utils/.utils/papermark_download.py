#!/usr/bin/env python3

import os
import sys
import time
import re
import argparse
import glob
from PIL import Image
import img2pdf
import ocrmypdf
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# Set up logging
def setup_logging(output_dir=None):
    """Set up logging to both console and file"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.handlers = []  # Clear existing handlers
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if output directory is provided
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(output_dir, 'papermark_downloader.log'))
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

# Initialize logger with console only for now
logger = setup_logging()

def setup_driver():
    """Set up and return a headless Chrome browser instance"""
    logger.info("Setting up headless Chrome browser...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Add additional headers to appear more like a real browser
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("Browser set up successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to set up browser: {e}")
        raise

def wait_for_element(driver, by, value, timeout=5, poll_frequency=0.1):
    """Wait for an element to be present with polling"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            element = driver.find_element(by, value)
            return element
        except NoSuchElementException:
            time.sleep(poll_frequency)
    
    # If we reach here, the element wasn't found within the timeout
    return None

def bypass_email_protection(driver, email="temp@example.com"):
    """Attempt to bypass email protection by submitting the form"""
    logger.info(f"Attempting to bypass email protection with {email}...")
    try:
        # Check if there's an email form
        email_input = wait_for_element(driver, By.ID, "email", timeout=3)
        if not email_input:
            logger.info("No email protection form found")
            return False
            
        logger.info("Found email input field")
        
        # Fill the email
        email_input.send_keys(email)
        logger.info("Entered email address")
        
        # Find and click the continue button
        continue_button = wait_for_element(driver, By.XPATH, "//button[contains(text(), 'Continue')]", timeout=3)
        if not continue_button:
            logger.warning("Could not find continue button")
            return False
            
        continue_button.click()
        logger.info("Clicked continue button")
        
        # Wait for email form to disappear (indicating success)
        start_time = time.time()
        timeout = 10
        while time.time() - start_time < timeout:
            try:
                driver.find_element(By.ID, "email")
                time.sleep(0.1)  # Email form still present, keep waiting
            except NoSuchElementException:
                logger.info(f"Email bypass successful after {time.time() - start_time:.2f} seconds")
                return True
        
        logger.warning("Email form stayed present after submit, bypass may have failed")
        return False
    except Exception as e:
        logger.error(f"Error bypassing email protection: {e}")
        return False

def get_current_page(driver):
    """Get the current page number and total pages from the pagination display"""
    pagination_element = wait_for_element(driver, By.XPATH, 
        "//div[contains(@class, 'flex h-8 items-center') or contains(@class, 'flex h-10 items-center')]", timeout=2)
    
    if pagination_element:
        pagination_text = pagination_element.text
        page_match = re.search(r'(\d+)\s*\/\s*(\d+)', pagination_text)
        if page_match:
            current_page = int(page_match.group(1))
            total_pages = int(page_match.group(2))
            return current_page, total_pages
    
    return None, None  # Return None if page number couldn't be determined

def wait_for_page_change(driver, current_page, timeout=5):
    """Wait for the page number to change from the current page"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        new_page, total_pages = get_current_page(driver)
        if new_page is not None and new_page != current_page:
            logger.info(f"Page changed from {current_page} to {new_page} in {time.time() - start_time:.2f} seconds")
            return new_page, total_pages
        time.sleep(0.1)
    
    # If we reach here, page didn't change
    new_page, total_pages = get_current_page(driver)
    return new_page, total_pages

def capture_all_slides(url, email=None, output_dir=None, max_failures=3):
    """Capture screenshots of all slides in the document"""
    # Setup output directory
    if not output_dir:
        parsed_url = url.split('/')
        document_id = parsed_url[-1] if len(parsed_url) > 1 else "papermark_document"
        output_dir = f"{document_id}_screenshots"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Update logger to include file logging
    global logger
    logger = setup_logging(output_dir)
    
    total_start_time = time.time()
    logger.info(f"Starting Papermark document screenshot capture for URL: {url}")
    logger.info(f"Created output directory: {output_dir}")
    
    # Log script parameters
    logger.info(f"Script parameters: email={email}, max_failures={max_failures}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"OS: {sys.platform}")
    
    driver = None
    try:
        # Set up the driver
        driver = setup_driver()
        
        # Navigate to the URL
        logger.info(f"Navigating to URL: {url}")
        driver.get(url)
        
        # Wait for the body element to load
        logger.info("Waiting for page to load...")
        body = wait_for_element(driver, By.TAG_NAME, "body", timeout=30)
        if not body:
            logger.error("Timeout waiting for page to load")
            raise TimeoutException("Page load timeout")
        
        logger.info("Page loaded successfully")
        
        # Wait for page content to stabilize
        start_time = time.time()
        max_wait = 5
        while time.time() - start_time < max_wait:
            # Try to find pagination element as indicator of complete load
            current_page, total_pages = get_current_page(driver)
            if current_page is not None:
                logger.info(f"Page fully loaded in {time.time() - start_time:.2f} seconds")
                break
            time.sleep(0.1)
        
        # Check if we need to bypass email protection
        if email:
            bypass_result = bypass_email_protection(driver, email)
            logger.info(f"Email protection bypass result: {bypass_result}")
            
            # Take a screenshot after bypass attempt
            screenshot_path = os.path.join(output_dir, "after_bypass.png")
            driver.save_screenshot(screenshot_path)
            logger.info(f"Saved post-bypass screenshot to {screenshot_path}")
        
        # Get current page and total pages
        current_page, total_pages = get_current_page(driver)
        if not current_page:
            current_page = 1
            logger.warning("Could not determine current page number, assuming page 1")
        
        if total_pages:
            logger.info(f"Document has {total_pages} pages according to pagination")
        else:
            logger.warning("Could not determine total page count from pagination")
        
        # Save page source for analysis
        page_source = driver.page_source
        source_path = os.path.join(output_dir, "page_source.html")
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(page_source)
        logger.info(f"Saved page source to {source_path}")
        
        # Take a screenshot of the initial page
        screenshot_path = os.path.join(output_dir, f"slide_{current_page:03d}.png")
        driver.save_screenshot(screenshot_path)
        logger.info(f"Saved screenshot of page {current_page} to {screenshot_path}")
        
        # Navigate through pages and capture screenshots
        page_times = []  # To track time per page
        consecutive_failures = 0  # Track consecutive failures to navigate
        page_num = current_page
        at_last_page = False
        
        # Main navigation loop
        while not at_last_page and consecutive_failures < max_failures:
            page_start_time = time.time()
            next_page = page_num + 1
            logger.info(f"Attempting to navigate to page {next_page}...")
            
            # Save the current page before attempting navigation
            pre_nav_page, pre_nav_total = get_current_page(driver)
            if pre_nav_page is None:
                pre_nav_page = page_num  # Fallback if can't read page number
            
            # First navigation attempt
            body.send_keys(Keys.RIGHT)
            
            # Wait for page change
            post_nav_page, post_nav_total = wait_for_page_change(driver, pre_nav_page, timeout=2)
            
            # If page didn't change, try a second time with more force
            if post_nav_page == pre_nav_page:
                logger.warning(f"First navigation attempt failed, trying again...")
                body.send_keys(Keys.RIGHT)
                post_nav_page, post_nav_total = wait_for_page_change(driver, pre_nav_page, timeout=2)
            
            # Check if we're at the last page
            if total_pages and pre_nav_page == total_pages:
                logger.info(f"Already at the last page ({pre_nav_page}/{total_pages}). Stopping capture.")
                at_last_page = True
                break
                
            # Check if navigation succeeded
            if post_nav_page != pre_nav_page and post_nav_page == next_page:
                # Navigation successful
                page_num = post_nav_page
                consecutive_failures = 0  # Reset failure counter
                
                # Take a screenshot of the new page
                screenshot_path = os.path.join(output_dir, f"slide_{page_num:03d}.png")
                driver.save_screenshot(screenshot_path)
                
                # Record time taken for this page
                page_time = time.time() - page_start_time
                page_times.append(page_time)
                
                logger.info(f"Successfully navigated to page {page_num} in {page_time:.2f} seconds")
                
                # Check if we've reached the last page
                if total_pages and page_num == total_pages:
                    logger.info(f"Reached last page ({page_num}/{total_pages}). Stopping capture.")
                    at_last_page = True
                    break
            else:
                # Navigation failed
                consecutive_failures += 1
                logger.warning(f"Failed to navigate to next page. Current page: {post_nav_page}, Expected: {next_page}")
                logger.warning(f"Consecutive failures: {consecutive_failures}/{max_failures}")
                
                # Check if we're at the last page (comparing pre and post total pages)
                if total_pages and post_nav_page == total_pages:
                    logger.info(f"Detected last page ({post_nav_page}/{total_pages}). Stopping capture.")
                    at_last_page = True
                    break
        
        # Check if we stopped due to failures
        if consecutive_failures >= max_failures:
            logger.info(f"Reached {consecutive_failures} consecutive navigation failures. Stopping capture.")
        
        # Count how many slides we actually captured
        slide_count = len([f for f in os.listdir(output_dir) if f.startswith("slide_") and f.endswith(".png")])
        total_time = time.time() - total_start_time
        
        # Calculate statistics
        if page_times:
            avg_time = sum(page_times) / len(page_times)
            min_time = min(page_times)
            max_time = max(page_times)
            logger.info(f"Time per page - Avg: {avg_time:.2f}s, Min: {min_time:.2f}s, Max: {max_time:.2f}s")
        
        logger.info(f"Successfully captured {slide_count} slides in {total_time:.2f} seconds")
        return output_dir, slide_count
            
    except Exception as e:
        logger.error(f"Error in screenshot capture process: {e}", exc_info=True)
        return output_dir, 0
    finally:
        if driver:
            logger.info("Closing browser")
            driver.quit()

def convert_screenshots_to_pdf(screenshots_dir, output_pdf):
    """Convert a directory of screenshots to a PDF file"""
    logger.info(f"Converting screenshots in {screenshots_dir} to PDF: {output_pdf}")
    
    # Get all screenshot files and sort them numerically
    screenshot_files = glob.glob(os.path.join(screenshots_dir, "slide_*.png"))
    screenshot_files.sort(key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))
    
    if not screenshot_files:
        logger.error(f"No screenshot files found in {screenshots_dir}")
        return False
    
    logger.info(f"Found {len(screenshot_files)} screenshot files")
    
    try:
        # Convert PNG files to PDF
        with open(output_pdf, "wb") as f:
            f.write(img2pdf.convert(screenshot_files))
        
        logger.info(f"Successfully created PDF: {output_pdf}")
        return True
    except Exception as e:
        logger.error(f"Error converting screenshots to PDF: {e}")
        return False

def compress_pdf(input_pdf, output_pdf, compression_level=3):
    """Compress a PDF file using ghostscript"""
    logger.info(f"Compressing PDF: {input_pdf} -> {output_pdf}")
    
    # Define compression levels
    # 0=default, 1=prepress, 2=printer, 3=ebook, 4=screen
    quality_map = {
        0: '/default',
        1: '/prepress',
        2: '/printer',
        3: '/ebook',
        4: '/screen'
    }
    
    quality = quality_map.get(compression_level, '/ebook')
    
    try:
        import subprocess
        
        # Check if ghostscript is installed
        try:
            subprocess.run(['gs', '--version'], capture_output=True, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error("Ghostscript not found. PDF compression requires ghostscript to be installed.")
            return False
        
        # Compress the PDF using ghostscript
        gs_cmd = [
            'gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
            f'-dPDFSETTINGS={quality}', '-dNOPAUSE', '-dQUIET', '-dBATCH',
            f'-sOutputFile={output_pdf}', input_pdf
        ]
        
        subprocess.run(gs_cmd, check=True)
        
        # Check file sizes for compression ratio
        input_size = os.path.getsize(input_pdf)
        output_size = os.path.getsize(output_pdf)
        compression_ratio = (1 - (output_size / input_size)) * 100
        
        logger.info(f"PDF compression successful. Compression ratio: {compression_ratio:.2f}%")
        logger.info(f"Original size: {input_size/1024/1024:.2f} MB, Compressed size: {output_size/1024/1024:.2f} MB")
        
        return True
    except Exception as e:
        logger.error(f"Error compressing PDF: {e}")
        return False

def add_ocr_to_pdf(input_pdf, output_pdf, languages=None):
    """Add OCR to a PDF file"""
    if not languages:
        languages = ["eng"]
    
    languages_str = "+".join(languages)
    logger.info(f"Adding OCR to PDF with languages: {languages_str}")
    
    try:
        # Add debug info about available tesseract languages
        import subprocess
        try:
            # Try to get installed tesseract languages
            result = subprocess.run(['tesseract', '--list-langs'], 
                                   capture_output=True, text=True, check=False)
            if result.returncode == 0:
                installed_langs = result.stdout.strip().split('\n')[1:]  # Skip the header line
                logger.info(f"Available Tesseract languages: {', '.join(installed_langs)}")
                
                # Filter out unavailable languages
                available_languages = [lang for lang in languages if lang in installed_langs]
                if not available_languages:
                    logger.warning(f"None of the requested languages {languages} are available in Tesseract.")
                    available_languages = ["eng"]  # Default to English
                
                if available_languages != languages:
                    logger.warning(f"Using only available languages: {available_languages}")
                    languages_str = "+".join(available_languages)
            else:
                logger.warning("Could not determine available Tesseract languages. Using English only.")
                languages_str = "eng"
        except Exception as e:
            logger.warning(f"Error checking available Tesseract languages: {e}")
            logger.warning("Defaulting to English only")
            languages_str = "eng"
        
        # Run OCR on the PDF
        ocrmypdf.ocr(
            input_pdf, 
            output_pdf,
            language=languages_str,
            optimize=1,  # Level 1 optimization (lossless)
            force_ocr=True,  # Force OCR even if text is detected
            progress_bar=False,  # Disable progress bar
            output_type="pdf",
            deskew=True,  # Deskew pages
            clean=True,  # Clean pages
            rotate_pages=True,  # Automatically rotate pages
            jobs=os.cpu_count()  # Use all CPU cores
        )
        
        logger.info(f"Successfully added OCR to PDF: {output_pdf}")
        return True
    except Exception as e:
        logger.error(f"Error adding OCR to PDF: {e}")
        return False

def process_slides_to_pdf(screenshots_dir, output_dir=None, languages=None):
    """Process slides from screenshots to OCR'd PDF"""
    # Set default output directory if not provided
    if not output_dir:
        output_dir = screenshots_dir
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Set output PDF paths
    slides_pdf = os.path.join(output_dir, "slides.pdf")
    slides_ocr_pdf = os.path.join(output_dir, "slides_ocr.pdf")
    slides_ocr_compressed_pdf = os.path.join(output_dir, "slides_ocr_compressed.pdf")
    
    # Set default languages if not provided
    if not languages:
        languages = ["eng"]
    
    start_time = time.time()
    logger.info(f"Starting PDF generation process from {screenshots_dir}")
    logger.info(f"Output files will be saved to: {output_dir}")
    logger.info(f"OCR languages: {languages}")
    
    # Step 1: Convert screenshots to PDF (without OCR)
    logger.info("Step 1: Converting screenshots to regular PDF...")
    if not convert_screenshots_to_pdf(screenshots_dir, slides_pdf):
        logger.error("Failed to convert screenshots to PDF. Exiting.")
        return False
    
    # Step 2: Create PDF with OCR
    logger.info("Step 2: Creating OCR'd PDF...")
    ocr_success = add_ocr_to_pdf(slides_pdf, slides_ocr_pdf, languages)
    
    if not ocr_success:
        # If OCR fails, try with just English
        if len(languages) > 1 and "eng" in languages:
            logger.warning("OCR failed with multiple languages. Trying with English only...")
            ocr_success = add_ocr_to_pdf(slides_pdf, slides_ocr_pdf, ["eng"])
            if ocr_success:
                logger.info(f"OCR completed successfully with English only.")
            else:
                # If still failing, copy the non-OCR'd PDF
                logger.warning("OCR failed. Using the non-OCR'd PDF as OCR version.")
                import shutil
                shutil.copy(slides_pdf, slides_ocr_pdf)
                logger.info(f"Copied non-OCR'd PDF to: {slides_ocr_pdf}")
                ocr_success = True  # Set to true since we have a PDF to compress
        else:
            # If not using multiple languages, copy the non-OCR'd PDF
            logger.warning("OCR failed. Using the non-OCR'd PDF as OCR version.")
            import shutil
            shutil.copy(slides_pdf, slides_ocr_pdf)
            logger.info(f"Copied non-OCR'd PDF to: {slides_ocr_pdf}")
            ocr_success = True  # Set to true since we have a PDF to compress
    
    # Step 3: Compress the OCR'd PDF
    if ocr_success and os.path.exists(slides_ocr_pdf):
        logger.info("Step 3: Compressing the OCR'd PDF...")
        compress_success = compress_pdf(slides_ocr_pdf, slides_ocr_compressed_pdf)
        if not compress_success:
            logger.warning("PDF compression failed. Using uncompressed OCR'd PDF.")
            import shutil
            shutil.copy(slides_ocr_pdf, slides_ocr_compressed_pdf)
            logger.info(f"Copied uncompressed OCR'd PDF to: {slides_ocr_compressed_pdf}")
    
    total_time = time.time() - start_time
    logger.info(f"PDF generation completed in {total_time:.2f} seconds")
    logger.info(f"PDF files saved:")
    logger.info(f"  - Regular PDF: {slides_pdf}")
    logger.info(f"  - OCR'd PDF: {slides_ocr_pdf}")
    logger.info(f"  - Compressed OCR'd PDF: {slides_ocr_compressed_pdf}")
    
    return True

def download_and_process_document(url, email=None, output_dir=None, languages=None, max_failures=3):
    """Download a Papermark document and convert it to multiple PDF formats"""
    total_start_time = time.time()
    logger.info("Starting combined Papermark document download and PDF processing")
    
    # Step 1: Capture all slides
    logger.info("Step 1: Capturing slides from Papermark document...")
    screenshots_dir, slide_count = capture_all_slides(url, email, output_dir, max_failures)
    
    if slide_count == 0:
        logger.error("Failed to capture any slides. Aborting PDF generation.")
        return False
    
    # Step 2: Generate PDFs (regular, OCR'd, and compressed)
    logger.info("Step 2: Generating PDF files...")
    pdf_success = process_slides_to_pdf(screenshots_dir, output_dir=screenshots_dir, languages=languages)
    
    if not pdf_success:
        logger.error("Failed to generate PDF files.")
        return False
    
    total_time = time.time() - total_start_time
    logger.info(f"Complete process finished in {total_time:.2f} seconds")
    logger.info(f"Captured {slide_count} slides and generated PDF files in: {screenshots_dir}")
    
    return True

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Download Papermark document and convert to multiple PDFs")
    parser.add_argument("url", nargs="?", help="URL of the Papermark document")
    parser.add_argument("--email", "-e", help="Email to use for protected documents")
    parser.add_argument("--output-dir", "-o", help="Output directory for screenshots and PDFs")
    parser.add_argument("--languages", "-l", nargs="+", default=["eng"],
                        help="OCR languages (default: eng)")
    parser.add_argument("--max-failures", "-f", type=int, default=3, 
                        help="Maximum consecutive navigation failures before stopping (default: 3)")
    return parser.parse_args()

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Get URL from arguments or prompt
    url = args.url
    if not url:
        url = input("Enter Papermark document URL: ")
    
    # Process all arguments
    email = args.email
    output_dir = args.output_dir
    languages = args.languages
    max_failures = args.max_failures
    
    # Download and process the document
    download_and_process_document(url, email, output_dir, languages, max_failures)
