#!/usr/bin/env python3
"""
Simple file uploader to dpaste.org
Usage: python upload_to_dpaste.py <file>
"""

import argparse
import os
import subprocess
import sys
import time
from typing import Tuple, Optional

# ANSI color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

# Logging functions with colors
def log_info(msg: str, no_newline: bool = False):
    """Print info message in blue"""
    end = '' if no_newline else '\n'
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}", end=end)

def log_success(msg: str):
    """Print success message in green"""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")

def log_warning(msg: str):
    """Print warning message in yellow"""
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")

def log_error(msg: str):
    """Print error message in red"""
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}", file=sys.stderr)

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def check_curl() -> bool:
    """Check if curl is available"""
    try:
        result = subprocess.run(['curl', '--version'], capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def upload_to_dpaste(filepath: str, expire_hours: int = 1) -> Tuple[str, Optional[str]]:
    """
    Upload file to dpaste.org using curl
    Returns: (url, http_code) on success, raises Exception on failure
    """
    # Convert hours to days (dpaste API uses days)
    expire_days = expire_hours / 24.0
    
    try:
        # Use curl with response code capture
        result = subprocess.run([
            'curl',
            '-s',  # Silent mode
            '-w', '%{http_code}',  # Write out HTTP code
            '-F', f'content=<{filepath}',
            '-F', f'expiry_days={expire_days:.6f}',  # 6 decimal places for precision
            '--max-time', '30',  # 30 second timeout
            'https://dpaste.org/api/'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Extract HTTP code (last 3 characters)
            full_response = result.stdout
            if len(full_response) >= 3:
                http_code = full_response[-3:]
                body = full_response[:-3]
                
                if http_code == '200':
                    # dpaste returns URL in quotes
                    url = body.strip().strip('"')
                    if url.startswith('https://dpaste.org/'):
                        return url, http_code
                    else:
                        raise Exception(f"Unexpected response format: {body}")
                else:
                    raise Exception(f"HTTP {http_code}: {body}")
            else:
                raise Exception(f"Invalid response: {full_response}")
        else:
            stderr = result.stderr.strip()
            if "Could not resolve host" in stderr:
                raise Exception("Network error: Could not connect to dpaste.org")
            elif "Connection timed out" in stderr:
                raise Exception("Network error: Connection timeout")
            else:
                raise Exception(f"curl failed with code {result.returncode}: {stderr}")
            
    except subprocess.TimeoutExpired:
        raise Exception("Upload timeout after 30 seconds")
    except FileNotFoundError:
        raise Exception("curl not found. Please install curl to use this script")

def main():
    parser = argparse.ArgumentParser(
        description='Upload file to dpaste.org (public paste service)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s myfile.md                        # Expires in 1 hour (default)
  %(prog)s script.py -e 24                  # Expires in 24 hours (1 day)
  %(prog)s data.txt --expire 168 --verbose  # Expires in 168 hours (7 days)

Note: dpaste.org is a public service. Do not upload sensitive information."""
    )
    
    parser.add_argument('file', help='File to upload')
    parser.add_argument('-e', '--expire', type=int, default=1,
                       help='Expiry time in hours (1-8760, default: 1)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show verbose output')
    
    args = parser.parse_args()
    
    # Check curl availability first
    if not check_curl():
        log_error("curl is not installed or not available in PATH")
        log_info("Please install curl: https://curl.se/download.html")
        sys.exit(1)
    
    # Validate file
    if not os.path.isfile(args.file):
        log_error(f"File '{args.file}' not found or not readable")
        parser.print_usage(sys.stderr)
        sys.exit(1)
    
    if not os.access(args.file, os.R_OK):
        log_error(f"File '{args.file}' is not readable (check permissions)")
        sys.exit(1)
    
    # Validate expiry (1 hour to 1 year)
    if args.expire < 1 or args.expire > 8760:  # 8760 hours = 365 days
        log_error(f"Expiry hours must be between 1 and 8760 (365 days)")
        sys.exit(1)
    
    # Check file size
    try:
        file_size = os.path.getsize(args.file)
        file_size_str = format_file_size(file_size)
        
        # Warn for large files
        if file_size > 10 * 1024 * 1024:  # 10MB
            log_warning(f"File is very large ({file_size_str})")
            log_warning("dpaste.org may reject files over 10MB")
        elif file_size > 1024 * 1024:  # 1MB
            log_warning(f"File is large ({file_size_str})")
            log_warning("dpaste.org may have size limits")
        elif file_size == 0:
            log_error("File is empty")
            sys.exit(1)
    except OSError as e:
        log_error(f"Could not get file size: {e}")
        sys.exit(1)
    
    # Show upload info
    if args.verbose:
        log_info(f"Uploading: {args.file}")
        log_info(f"Expires in: {args.expire} hour{'s' if args.expire != 1 else ''}")
        if args.expire >= 24:
            days = args.expire / 24
            log_info(f"  ({days:.1f} day{'s' if days != 1 else ''})")
        log_info(f"File size: {file_size_str} ({file_size:,} bytes)")
    
    # Upload with progress indication
    log_info("Uploading to dpaste.org...", no_newline=True)
    start_time = time.time()
    
    try:
        url, http_code = upload_to_dpaste(args.file, args.expire)
        elapsed = time.time() - start_time
        
        print(f" done ({elapsed:.1f}s)")
        log_success("Upload successful!")
        print(f"🔗 URL: {url}")
        
        if args.verbose:
            log_info("Details:")
            log_info("  - Service: dpaste.org")
            log_info("  - Public: Yes")
            log_info(f"  - Expires: {args.expire} hour{'s' if args.expire != 1 else ''}")
            if args.expire >= 24:
                days = args.expire / 24
                log_info(f"  - ({days:.1f} day{'s' if days != 1 else ''})")
            log_info(f"  - Direct link: {url}")
            log_info(f"  - Upload time: {elapsed:.1f} seconds")
        
        # Copy to clipboard if possible (optional enhancement)
        try:
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['pbcopy'], input=url, text=True, capture_output=True)
                if args.verbose:
                    log_info("  - URL copied to clipboard")
            elif sys.platform == 'linux':  # Linux
                # Try xclip first, then xsel
                for cmd in ['xclip -selection clipboard', 'xsel --clipboard --input']:
                    try:
                        subprocess.run(cmd.split(), input=url, text=True, capture_output=True)
                        if args.verbose:
                            log_info("  - URL copied to clipboard")
                        break
                    except:
                        continue
        except:
            pass  # Clipboard copy is optional
        
    except KeyboardInterrupt:
        print()  # New line after ^C
        log_warning("Upload cancelled by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print()  # New line after "Uploading..."
        log_error(f"Upload failed: {e}")
        log_info("You can try manually at: https://dpaste.org/")
        
        # More helpful error messages
        if "Network error" in str(e):
            log_info("Check your internet connection")
        elif "curl not found" in str(e):
            log_info("Install curl: https://curl.se/download.html")
        
        sys.exit(1)

if __name__ == '__main__':
    main()