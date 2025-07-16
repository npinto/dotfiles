#!/usr/bin/env python3
"""
DocSend Downloader - Enhanced version with verbose OCR and title extraction
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table

console = Console()


def get_image_hash(image_data):
    """Get hash of image data."""
    return hashlib.md5(image_data).hexdigest()


def extract_title_from_image(image_path):
    """Try to extract title from the first slide using OCR."""
    console.print("\n[yellow]Attempting to extract document title from first slide...[/yellow]")
    
    try:
        # Use tesseract to extract text from first slide
        result = subprocess.run([
            'tesseract', str(image_path), 'stdout', '--psm', '3'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            text = result.stdout
            # Look for title-like text (first few lines, longer phrases)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            if lines:
                # Try to find a good title candidate
                # Usually the title is in the first few lines and is substantial
                for i, line in enumerate(lines[:5]):
                    # Skip very short lines or lines that look like dates/numbers
                    if len(line) > 10 and not re.match(r'^[\d\s\-/]+$', line):
                        # Clean up the title
                        title = re.sub(r'[^\w\s\-]', ' ', line)
                        title = ' '.join(title.split())[:50]  # Limit length
                        if title:
                            console.print(f"[green]✓ Found potential title: '{title}'[/green]")
                            return title
                
                # If no good title found, use first substantial line
                first_line = lines[0] if lines else ""
                if len(first_line) > 5:
                    title = re.sub(r'[^\w\s\-]', ' ', first_line)
                    title = ' '.join(title.split())[:50]
                    console.print(f"[yellow]Using first line as title: '{title}'[/yellow]")
                    return title
        
    except FileNotFoundError:
        console.print("[yellow]Tesseract not installed - cannot extract title from image[/yellow]")
        console.print("Install with: brew install tesseract")
    except Exception as e:
        console.print(f"[yellow]Could not extract title: {e}[/yellow]")
    
    return None


def suggest_better_title_with_llm(pdf_path, fallback_title):
    """Use phi3.5 mini to suggest a better title based on OCR'd PDF content."""
    if not HF_AVAILABLE:
        console.print("[yellow]Hugging Face transformers not available - install with: pip install transformers torch[/yellow]")
        return fallback_title
    
    console.print("\n[cyan]🤖 Using phi3.5 mini to suggest a better title...[/cyan]")
    
    try:
        # Extract text from the OCR'd PDF
        console.print("   Extracting text from OCR PDF...")
        result = subprocess.run([
            'pdftotext', '-layout', '-nopgbrk', str(pdf_path), '-'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            console.print("[yellow]pdftotext not available - install with: brew install poppler[/yellow]")
            return fallback_title
        
        pdf_text = result.stdout
        
        # Take first 2000 characters to avoid token limits
        pdf_text = pdf_text[:2000]
        
        if not pdf_text.strip():
            console.print("[yellow]No text extracted from PDF[/yellow]")
            return fallback_title
        
        console.print("   Loading phi3.5 mini model...")
        
        # Load phi3.5 mini model
        model_name = "microsoft/Phi-3.5-mini-instruct"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name, 
            torch_dtype=torch.float32,  # Use float32 for compatibility
            device_map="cpu"  # Use CPU to avoid MPS issues
        )
        
        # Set pad token if not present
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Create prompt for title suggestion
        prompt = f"""Based on the following document content, suggest a concise, descriptive title (max 50 characters):

{pdf_text}

Suggested title:"""
        
        console.print("   Generating title suggestion...")
        
        # Tokenize and generate
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=50,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode the response
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract the suggested title (everything after "Suggested title:")
        if "Suggested title:" in response:
            suggested_title = response.split("Suggested title:")[-1].strip()
            # Clean up the title
            suggested_title = re.sub(r'[^\w\s\-]', ' ', suggested_title)
            suggested_title = ' '.join(suggested_title.split())[:50]
            
            if suggested_title and len(suggested_title) > 5:
                console.print(f"[green]✓ LLM suggested title: '{suggested_title}'[/green]")
                console.print(f"[dim]Original title: '{fallback_title}'[/dim]")
                return suggested_title
        
        console.print("[yellow]Could not generate a good title suggestion[/yellow]")
        return fallback_title
        
    except Exception as e:
        console.print(f"[yellow]Error with LLM title suggestion: {e}[/yellow]")
        return fallback_title


def authenticate_with_email(session, url, email, passcode, headers):
    """Try to authenticate with a specific email."""
    console.print(f"Trying email: [bold cyan]{email}[/bold cyan]")
    
    # Get the page first to extract CSRF token
    response = session.get(url)
    
    # Extract CSRF token
    csrf_match = re.search(r'name="authenticity_token"\s+value="([^"]+)"', response.text)
    csrf_token = csrf_match.group(1) if csrf_match else None
    
    auth_data = {
        'utf8': '✓',
        '_method': 'patch',
        'link_auth_form[email]': email,
        'link_auth_form[passcode]': passcode,
        'commit': 'Continue'
    }
    
    # Add CSRF token if found
    if csrf_token:
        auth_data['authenticity_token'] = csrf_token
    
    auth_headers = headers.copy()
    auth_headers.update({
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://docsend.com',
        'Referer': url,
    })
    
    auth_response = session.post(url, data=auth_data, headers=auth_headers, allow_redirects=True)
    
    # Check if authentication was successful
    if auth_response.status_code in [200, 302] or (auth_response.history and any(r.status_code == 302 for r in auth_response.history)):
        # Additional check: try to access page_data/1
        document_code = url.strip('/').split('/')[-1]
        test_url = f"https://docsend.com/view/{document_code}/page_data/1"
        test_response = session.get(test_url, headers={'Accept': 'application/json'})
        
        if test_response.status_code == 200:
            try:
                data = test_response.json()
                if 'imageUrl' in data:
                    console.print(f"[bold green]✓ Authentication successful with {email}[/bold green]")
                    return True
            except:
                pass
    
    console.print(f"[yellow]✗ Authentication failed with {email}[/yellow]")
    return False


def download_image_batch(session, document_code, start_idx, batch_size=8):
    """Download a batch of images in parallel."""
    console.print(f"[cyan]Downloading batch: slides {start_idx} to {start_idx + batch_size - 1}[/cyan]")
    
    def download_single(idx):
        page_url = f"https://docsend.com/view/{document_code}/page_data/{idx}"
        
        try:
            resp = session.get(page_url, headers={'Accept': 'application/json'}, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                image_url = data.get('imageUrl')
                
                if image_url:
                    img_resp = session.get(image_url, timeout=30)
                    
                    if img_resp.status_code == 200:
                        img_hash = get_image_hash(img_resp.content)
                        console.print(f"  ✓ Slide {idx}: Downloaded (hash: {img_hash[:8]}...)")
                        return idx, img_hash, len(img_resp.content), img_resp.content
                    else:
                        console.print(f"  ✗ Slide {idx}: Image download failed")
        except Exception as e:
            console.print(f"  ✗ Slide {idx}: Error - {str(e)}")
        
        return idx, None, None, None
    
    # Download batch in parallel
    results = {}
    with ThreadPoolExecutor(max_workers=min(batch_size, 8)) as executor:
        futures = {executor.submit(download_single, i): i 
                  for i in range(start_idx, start_idx + batch_size)}
        
        for future in as_completed(futures):
            idx, img_hash, size, content = future.result()
            if img_hash:
                results[idx] = (img_hash, size, content)
    
    return results


def detect_slide_count_auto(session, document_code):
    """Automatically detect slide count without user interaction."""
    console.print("\n[bold yellow]Auto-detecting slide count...[/bold yellow]\n")
    
    all_hashes = {}
    batch_size = 8
    last_valid_slide = 0
    
    # First, check single slides to handle small documents
    console.print("[cyan]Checking first few slides individually...[/cyan]")
    for i in range(1, 6):
        results = download_image_batch(session, document_code, i, 1)
        if results:
            last_valid_slide = i
            for idx, (img_hash, size, content) in results.items():
                # Check for duplicates
                for prev_idx, (prev_hash, prev_size) in all_hashes.items():
                    if prev_hash == img_hash and idx > prev_idx:
                        console.print(f"\n[bold green]✓ Found duplicate: slide {idx} matches slide {prev_idx}[/bold green]")
                        console.print(f"[bold green]Document has {prev_idx} slides[/bold green]\n")
                        return prev_idx
                all_hashes[idx] = (img_hash, size)
        else:
            # No valid slide at position i
            if i == 1:
                console.print("[red]Cannot access slide 1 - authentication may have failed[/red]")
                return None
            else:
                console.print(f"\n[bold green]✓ No valid slide at position {i}[/bold green]")
                console.print(f"[bold green]Document has {i-1} slides[/bold green]\n")
                return i - 1
    
    # For larger documents, use batch mode
    console.print("\n[cyan]Document has more than 5 slides, switching to batch mode...[/cyan]")
    
    for batch_num in range(1, 20):  # Check up to 160 slides
        start_idx = 5 + (batch_num - 1) * batch_size + 1
        
        console.print(f"\n[bold]Batch {batch_num}:[/bold]")
        batch_results = download_image_batch(session, document_code, start_idx, batch_size)
        
        if not batch_results:
            # Empty batch - we've reached the end
            console.print(f"\n[bold green]✓ Empty batch - document ends at slide {last_valid_slide}[/bold green]\n")
            return last_valid_slide
        
        # Update last valid slide
        if batch_results:
            last_valid_slide = max(batch_results.keys())
        
        # If batch is partially empty, we might be at the end
        if len(batch_results) < batch_size:
            console.print(f"\n[yellow]Batch returned only {len(batch_results)} slides (expected {batch_size})[/yellow]")
            
            # Check if the missing slides are at the end
            missing_at_end = True
            for i in range(start_idx, start_idx + batch_size):
                if i <= last_valid_slide and i not in batch_results:
                    missing_at_end = False
                    break
            
            if missing_at_end:
                console.print(f"[bold green]✓ Reached end of document at slide {last_valid_slide}[/bold green]\n")
                return last_valid_slide
        
        # Check for duplicates
        for idx, (img_hash, size, content) in batch_results.items():
            for prev_idx, (prev_hash, prev_size) in all_hashes.items():
                if prev_hash == img_hash and size == prev_size and idx > prev_idx + 2:
                    console.print(f"\n[bold green]✓ Found duplicate: slide {idx} matches slide {prev_idx}[/bold green]")
                    console.print(f"[bold green]Document has {prev_idx} slides[/bold green]\n")
                    return prev_idx
            
            all_hashes[idx] = (img_hash, size)
    
    # If we've checked many slides without finding the end
    console.print(f"\n[yellow]Checked {last_valid_slide} slides without finding document end[/yellow]")
    console.print(f"[bold green]Using last valid slide: {last_valid_slide}[/bold green]\n")
    return last_valid_slide


def download_all_slides_parallel(session, document_code, slide_count, output_dir, max_workers=8):
    """Download all slides in parallel with progress tracking."""
    console.print(f"\n[bold]Downloading all {slide_count} slides in parallel (workers: {max_workers})...[/bold]\n")
    
    def download_slide(slide_num):
        """Download a single slide."""
        try:
            page_url = f"https://docsend.com/view/{document_code}/page_data/{slide_num}"
            resp = session.get(page_url, headers={'Accept': 'application/json'}, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                image_url = data.get('imageUrl')
                
                if image_url:
                    img_resp = session.get(image_url, timeout=30)
                    
                    if img_resp.status_code == 200:
                        filename = f"slide_{slide_num:03d}.png"
                        filepath = output_dir / filename
                        
                        with open(filepath, 'wb') as f:
                            f.write(img_resp.content)
                        
                        return slide_num, True, None
        
        except Exception as e:
            return slide_num, False, str(e)
        
        return slide_num, False, "Failed to download"
    
    successful = 0
    failed = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        console=console
    ) as progress:
        
        download_task = progress.add_task("[cyan]Downloading slides...", total=slide_count)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            futures = {executor.submit(download_slide, i): i for i in range(1, slide_count + 1)}
            
            # Process completed downloads
            for future in as_completed(futures):
                slide_num, success, error = future.result()
                
                if success:
                    successful += 1
                else:
                    failed.append((slide_num, error))
                
                progress.update(download_task, advance=1)
    
    console.print(f"\n✓ Downloaded {successful}/{slide_count} slides")
    
    if failed:
        console.print(f"✗ Failed: {len(failed)} slides")
        for slide, error in failed[:5]:
            console.print(f"  - Slide {slide}: {error}")
        if len(failed) > 5:
            console.print(f"  ... and {len(failed) - 5} more")
    
    return successful


def create_pdfs_verbose(output_dir, document_code, document_title=None, ocr_jobs=None, use_llm_title=False):
    """Create PDFs with OCR and compression - with verbose progress."""
    console.print("\n[bold]Creating PDFs with OCR and compression...[/bold]\n")
    
    slides = sorted(output_dir.glob("slide_*.png"))
    if not slides:
        console.print("[red]No slides found to create PDF[/red]")
        return
    
    # Get today's date in YYYY-MM-DD format
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Use document title if available, otherwise use code
    title_part = document_title if document_title else document_code
    base_name = f"{today} {title_part}"
    
    # 1. Create raw PDF
    try:
        import img2pdf
        pdf_path = output_dir / f"{base_name}.pdf"
        console.print("📄 Creating raw PDF...")
        console.print(f"   Input: {len(slides)} PNG files")
        console.print(f"   Output: {pdf_path.name}")
        
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert([str(s) for s in slides]))
        
        size_mb = pdf_path.stat().st_size / (1024 * 1024)
        console.print(f"   ✓ Created: {pdf_path.name} ({size_mb:.1f} MB)")
        
    except ImportError:
        console.print("[yellow]img2pdf not installed, trying ImageMagick...[/yellow]")
        try:
            pdf_path = output_dir / f"{base_name}.pdf"
            subprocess.run(["convert"] + [str(s) for s in slides] + [str(pdf_path)], check=True)
            console.print(f"  ✓ Created: {pdf_path}")
        except:
            console.print("[red]Could not create PDF - install img2pdf or ImageMagick[/red]")
            return
    
    # 2. Create OCR PDF with progress bar
    if pdf_path.exists():
        try:
            ocr_path = output_dir / f"{base_name} (OCR).pdf"
            console.print("\n🔍 Creating searchable PDF with OCR...")
            console.print(f"   Input: {pdf_path.name}")
            console.print(f"   Output: {ocr_path.name}")
            # Show CPU usage info
            import os
            cpu_count = ocr_jobs or os.cpu_count() or 4
            console.print(f"   Settings: rotate pages, deskew, optimize, {cpu_count} CPU core{'s' if cpu_count != 1 else ''}")
            
            # Count total pages for progress bar
            total_pages = len(slides)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total} pages)"),
                console=console
            ) as progress:
                
                ocr_task = progress.add_task("   Processing", total=total_pages)
                
                # Run OCR in a separate thread to update progress
                import threading
                import time
                
                def run_ocr():
                    # Use specified number of CPU cores for OCR processing
                    import os
                    cpu_count = ocr_jobs or os.cpu_count() or 4
                    return subprocess.run([
                        "ocrmypdf",
                        "--rotate-pages",
                        "--deskew", 
                        "--optimize", "3",
                        "--jobs", str(cpu_count),  # Use multiple CPU cores
                        str(pdf_path),
                        str(ocr_path)
                    ], capture_output=True, text=True)
                
                # Start OCR in thread
                result_container = []
                ocr_thread = threading.Thread(target=lambda: result_container.append(run_ocr()))
                ocr_thread.start()
                
                # Update progress bar while OCR runs
                pages_per_second = 0.5  # Estimate based on typical OCR speed
                elapsed_time = 0
                while ocr_thread.is_alive():
                    time.sleep(0.1)
                    elapsed_time += 0.1
                    estimated_pages = min(int(elapsed_time * pages_per_second), total_pages - 1)
                    progress.update(ocr_task, completed=estimated_pages)
                
                ocr_thread.join()
                result = result_container[0]
                
                # Complete the progress bar
                progress.update(ocr_task, completed=total_pages)
            
            if result.returncode == 0:
                size_mb = ocr_path.stat().st_size / (1024 * 1024)
                console.print(f"   ✓ Created: {ocr_path.name} ({size_mb:.1f} MB)")
                
                # Try to get a better title using LLM if requested
                if use_llm_title and document_title:
                    llm_title = suggest_better_title_with_llm(ocr_path, document_title)
                    if llm_title != document_title:
                        # Update the title for subsequent files
                        document_title = llm_title
                        # Rename the OCR file with the better title
                        today = datetime.now().strftime("%Y-%m-%d")
                        new_base_name = f"{today} {document_title}"
                        new_ocr_path = output_dir / f"{new_base_name} (OCR).pdf"
                        if new_ocr_path != ocr_path:
                            ocr_path.rename(new_ocr_path)
                            ocr_path = new_ocr_path
                            console.print(f"   ✓ Renamed to: {ocr_path.name}")
                        
                        # Also rename the raw PDF
                        old_raw_path = output_dir / f"{base_name}.pdf"
                        new_raw_path = output_dir / f"{new_base_name}.pdf"
                        if old_raw_path.exists() and new_raw_path != old_raw_path:
                            old_raw_path.rename(new_raw_path)
                            console.print(f"   ✓ Renamed raw PDF to: {new_raw_path.name}")
                        
                        # Update base_name for compression step
                        base_name = new_base_name
                        
            else:
                console.print(f"   ✗ OCR failed: {result.stderr if result.stderr else 'Unknown error'}")
                return  # Don't proceed to compression if OCR failed
                
        except FileNotFoundError:
            console.print("[yellow]  ocrmypdf not installed - skipping OCR[/yellow]")
            console.print("  Install with: brew install ocrmypdf")
    
    # 3. Create compressed PDF with progress
    if (output_dir / f"{base_name} (OCR).pdf").exists():
        try:
            compressed_path = output_dir / f"{base_name} (OCR compressed).pdf"
            console.print("\n🗜️  Creating compressed PDF...")
            console.print(f"   Input: {ocr_path.name}")
            console.print(f"   Output: {compressed_path.name}")
            console.print("   Compression settings:")
            console.print("     - PDF compatibility: 1.4")
            console.print("     - Quality preset: ebook (150 dpi)")
            console.print("   Compressing...")
            
            result = subprocess.run([
                "gs",
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                "-dPDFSETTINGS=/ebook",
                "-dNOPAUSE",
                "-dBATCH",
                f"-sOutputFile={compressed_path}",
                str(output_dir / f"{base_name} (OCR).pdf")
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                size_mb = compressed_path.stat().st_size / (1024 * 1024)
                original_size = ocr_path.stat().st_size / (1024 * 1024)
                reduction = ((original_size - size_mb) / original_size) * 100
                console.print(f"   ✓ Created: {compressed_path.name} ({size_mb:.1f} MB)")
                console.print(f"   ✓ Size reduction: {reduction:.1f}%")
                
                # Show final file sizes comparison
                console.print("\n[bold]Final file sizes:[/bold]")
                for pdf in [pdf_path, ocr_path, compressed_path]:
                    if pdf.exists():
                        size_mb = pdf.stat().st_size / (1024 * 1024)
                        console.print(f"  {pdf.name}: {size_mb:.1f} MB")
            else:
                console.print(f"   ✗ Compression failed: {result.stderr}")
                
        except FileNotFoundError:
            console.print("[yellow]  Ghostscript not installed - skipping compression[/yellow]")
            console.print("  Install with: brew install ghostscript")


def download_docsend(url, email="nicolas.pinto@gmail.com", passcode="", slide_count=None, max_workers=8, ocr_jobs=None, use_llm_title=False):
    """Download DocSend presentation with enhanced features."""
    
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    session.headers.update(headers)
    
    # Extract document code - strip query parameters and fragments
    parsed_url = urlparse(url)
    # Clean path by removing query parameters and fragments
    clean_path = parsed_url.path.strip('/')
    document_code = clean_path.split('/')[-1]
    
    # Ensure document code doesn't contain query parameters
    if '?' in document_code:
        document_code = document_code.split('?')[0]
    if '#' in document_code:
        document_code = document_code.split('#')[0]
        
    # Rebuild clean URL without query parameters
    clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    url = clean_url  # Use clean URL for all subsequent requests
    
    console.print(f"\n[bold cyan]DocSend Downloader (Enhanced)[/bold cyan]")
    console.print(f"Document URL: {url}")
    console.print(f"Document Code: {document_code}")
    console.print(f"Parallel workers: {max_workers}")
    
    # Initial request and authentication
    console.print("\n[bold]Checking authentication requirements...[/bold]")
    response = session.get(url)
    
    authenticated_email = None
    
    if 'link_auth_form' in response.text:
        console.print(f"[yellow]Authentication required[/yellow]")
        
        # Try privacy email first
        privacy_email = "platypus@gmail.com"
        console.print(f"\n[bold]Attempting privacy-preserving authentication...[/bold]")
        
        if authenticate_with_email(session, url, privacy_email, passcode, headers):
            authenticated_email = privacy_email
        else:
            # Privacy email failed, try user email
            console.print(f"\n[bold]Privacy email failed, trying user-provided email...[/bold]")
            
            if authenticate_with_email(session, url, email, passcode, headers):
                authenticated_email = email
            else:
                console.print(f"\n[red]Authentication failed with both emails[/red]")
                console.print(f"[red]Unable to access document[/red]")
                return None
    else:
        console.print("[green]✓ No authentication required - document is public[/green]")
    
    if authenticated_email:
        console.print(f"\n[bold green]📧 Successfully authenticated with: {authenticated_email}[/bold green]")
    
    # Auto-detect slide count
    if not slide_count:
        detected = detect_slide_count_auto(session, document_code)
        
        if not detected:
            console.print("[red]Failed to detect slide count[/red]")
            return None
            
        slide_count = detected
    
    # Create output directory
    output_dir = Path(f"{document_code}_downloads")
    output_dir.mkdir(exist_ok=True)
    
    # Download all slides in parallel
    successful = download_all_slides_parallel(session, document_code, slide_count, output_dir, max_workers)
    
    # Try to extract title from first slide
    document_title = None
    first_slide = output_dir / "slide_001.png"
    if first_slide.exists():
        document_title = extract_title_from_image(first_slide)
    
    # Create PDFs with verbose output
    if successful > 0:
        create_pdfs_verbose(output_dir, document_code, document_title, ocr_jobs, use_llm_title)
    
    # Final summary
    console.print("\n[bold green]✓ Complete![/bold green]")
    
    # Show what was created
    table = Table(title="Files Created")
    table.add_column("File", style="cyan")
    table.add_column("Size", style="green")
    
    for file in sorted(output_dir.iterdir()):
        if file.is_file():
            size_kb = file.stat().st_size / 1024
            if size_kb > 1024:
                size_str = f"{size_kb/1024:.1f} MB"
            else:
                size_str = f"{size_kb:.1f} KB"
            table.add_row(file.name, size_str)
    
    console.print(table)
    
    if authenticated_email:
        console.print(f"\n[dim]Downloaded using: {authenticated_email}[/dim]")
    
    if document_title:
        console.print(f"[dim]Document title: {document_title}[/dim]")
    
    return output_dir


def main():
    parser = argparse.ArgumentParser(
        description="DocSend downloader with enhanced OCR progress and title extraction"
    )
    
    parser.add_argument("url", help="DocSend URL")
    parser.add_argument("--email", default="nicolas.pinto@gmail.com", help="Fallback email if privacy email fails")
    parser.add_argument("--passcode", default="", help="Passcode if required")
    parser.add_argument("--slides", type=int, help="Override automatic detection")
    parser.add_argument("--workers", type=int, default=8, help="Number of parallel download workers (default: 8)")
    parser.add_argument("--ocr-jobs", type=int, help="Number of CPU cores for OCR processing (default: all available)")
    parser.add_argument("--llm-title", action="store_true", help="Use phi3.5 mini LLM to suggest better title from OCR content")
    
    args = parser.parse_args()
    
    download_docsend(args.url, args.email, args.passcode, args.slides, args.workers, args.ocr_jobs, args.llm_title)


if __name__ == "__main__":
    main()