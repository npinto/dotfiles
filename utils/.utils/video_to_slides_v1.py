#!/usr/bin/env python3
"""
Video to Slides Converter using FFmpeg - Enhanced Version

Multi-stage deduplication pipeline:
1. FFmpeg extraction at 1fps with mpdecimate
2. Perceptual hash-based deduplication (dhash)
3. Content-based slide detection (remove video-like frames)

Improvements:
- Better deduplication to reduce 900+ frames to ~200
- Clean OCR output (no spam)
- Slide detection to remove non-slide frames

Author: Nicolas Pinto
License: MIT
"""

import argparse
import atexit
import io
import json
import logging
import multiprocessing
import queue
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List
import numpy as np

try:
    import img2pdf
    import ocrmypdf
    from PIL import Image
    import imagehash
    import cv2
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.table import Table
    from rich.live import Live
except ImportError as e:
    print(f"Error: Missing required Python package: {e}")
    print(
        "Please install required packages: pip install rich Pillow img2pdf ocrmypdf imagehash opencv-python"
    )
    sys.exit(1)

# Try to import better-ffmpeg-progress
try:
    from better_ffmpeg_progress import FfmpegProcess, FfmpegProcessError
    HAS_BETTER_FFMPEG = True
except ImportError:
    HAS_BETTER_FFMPEG = False


# Constants
DEFAULT_FPS = 1.0
DEFAULT_MPDECIMATE_HI = 2048  # Higher threshold for presentations
DEFAULT_MPDECIMATE_LO = 1024  # Higher threshold for presentations
DEFAULT_MPDECIMATE_FRAC = 0.5  # More aggressive for presentations
STATE_FILE = "state.json"
LOG_FILE = "process.log"
DEFAULT_WORKERS = min(multiprocessing.cpu_count(), 8)
BATCH_SIZE = 50  # Smaller batches for better progress tracking
DHASH_SIZE = 16  # Size for dhash computation
HAMMING_THRESHOLD = 10  # Hamming distance threshold for similarity

# Global console for rich output
console = Console()

# Global state for cleanup
temp_dirs: list[Path] = []


@dataclass
class Config:
    """Configuration for video processing."""

    fps: float = DEFAULT_FPS
    mpdecimate_hi: int = DEFAULT_MPDECIMATE_HI
    mpdecimate_lo: int = DEFAULT_MPDECIMATE_LO
    mpdecimate_frac: float = DEFAULT_MPDECIMATE_FRAC
    skip_ocr: bool = False
    skip_compress: bool = False
    dry_run: bool = False
    debug: bool = False
    config_file: Optional[Path] = None
    output_dir: Optional[Path] = None
    video_path: Optional[Path] = None
    resume_state: dict = field(default_factory=dict)
    workers: int = DEFAULT_WORKERS
    batch_size: int = BATCH_SIZE
    dhash_size: int = DHASH_SIZE
    hamming_threshold: int = HAMMING_THRESHOLD
    min_text_score: float = 0.3  # Minimum text density for slide detection
    edge_threshold: float = 50.0  # Edge density threshold for slide detection


def compute_dhash(image_path: Path, hash_size: int = DHASH_SIZE) -> imagehash.ImageHash:
    """Compute difference hash for an image.

    Args:
        image_path: Path to image
        hash_size: Size of hash (default: 16)

    Returns:
        ImageHash object
    """
    img = Image.open(image_path)
    return imagehash.dhash(img, hash_size=hash_size)


def compute_hash_for_frame(
    frame_path: Path, hash_size: int = DHASH_SIZE
) -> Tuple[Path, Optional[imagehash.ImageHash]]:
    """Compute hash for a single frame (module-level function for multiprocessing).
    
    Args:
        frame_path: Path to frame image
        hash_size: Size of dhash
        
    Returns:
        Tuple of (frame_path, hash_value or None if error)
    """
    try:
        return frame_path, compute_dhash(frame_path, hash_size)
    except Exception as e:
        logging.warning(f"Error computing hash for {frame_path}: {e}")
        return frame_path, None


def check_frame_for_slide(
    frame_path: Path, min_text_score: float = 0.3, edge_threshold: float = 50.0
) -> Tuple[Path, bool]:
    """Check if a frame is a slide (module-level function for multiprocessing).
    
    Args:
        frame_path: Path to frame image
        min_text_score: Minimum text density score
        edge_threshold: Edge density threshold
        
    Returns:
        Tuple of (frame_path, is_slide_bool)
    """
    return frame_path, is_slide_frame(frame_path, min_text_score, edge_threshold)


def detect_text_density(image_path: Path) -> float:
    """Detect text density in an image using edge detection.

    Args:
        image_path: Path to image

    Returns:
        Text density score (0.0-1.0)
    """
    try:
        # Read image in grayscale
        img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0.0

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(img, (5, 5), 0)

        # Apply Canny edge detection
        edges = cv2.Canny(blurred, 50, 150)

        # Calculate edge density
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])

        # Apply adaptive thresholding to find text-like regions
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        # Find contours (potential text regions)
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Filter contours by size (text-like regions)
        text_contours = []
        img_area = img.shape[0] * img.shape[1]
        for contour in contours:
            area = cv2.contourArea(contour)
            # Text regions are typically small to medium sized
            if 50 < area < img_area * 0.1:
                text_contours.append(contour)

        # Calculate text density based on number of text-like contours
        text_density = len(text_contours) / (img.shape[0] * img.shape[1] / 1000)
        text_density = min(text_density, 1.0)  # Cap at 1.0

        # Combine edge density and text density
        combined_score = edge_density * 0.3 + text_density * 0.7

        return combined_score

    except Exception as e:
        logging.warning(f"Error detecting text density: {e}")
        return 0.0


def is_slide_frame(
    image_path: Path, min_text_score: float = 0.3, edge_threshold: float = 50.0
) -> bool:
    """Determine if a frame is likely a slide (not video content).

    Args:
        image_path: Path to image
        min_text_score: Minimum text density score
        edge_threshold: Edge density threshold

    Returns:
        True if frame appears to be a slide
    """
    try:
        # Get text density score
        text_score = detect_text_density(image_path)

        # Read image for additional checks
        img = cv2.imread(str(image_path))
        if img is None:
            return False

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Check for uniform background (common in slides)
        std_dev = np.std(gray)

        # Slides typically have:
        # - High text density
        # - Low overall standard deviation (uniform backgrounds)
        # - Sharp edges (text and diagrams)

        # Calculate edge sharpness
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        edge_sharpness = laplacian.var()

        # Decision logic
        is_slide = (
            text_score > min_text_score  # Has significant text
            or (
                std_dev < 80 and edge_sharpness > edge_threshold
            )  # Uniform with sharp edges
            or (
                text_score > 0.2 and std_dev < 100
            )  # Some text with relatively uniform background
        )

        return is_slide

    except Exception as e:
        logging.warning(f"Error checking if slide frame: {e}")
        return True  # Default to keeping the frame


def deduplicate_with_dhash(
    frames: List[Path],
    hamming_threshold: int = HAMMING_THRESHOLD,
    hash_size: int = DHASH_SIZE,
    workers: int = DEFAULT_WORKERS,
) -> List[Path]:
    """Deduplicate frames using difference hashing.

    Args:
        frames: List of frame paths
        hamming_threshold: Maximum Hamming distance for similarity
        hash_size: Size of dhash
        workers: Number of parallel workers

    Returns:
        List of unique frame paths
    """
    console.print(
        f"\n[bold]Stage 2: Deduplicating {len(frames)} frames using dhash...[/bold]"
    )

    # Compute hashes in parallel
    frame_hashes = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Computing perceptual hashes...", total=len(frames)
        )

        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(compute_hash_for_frame, frame, hash_size) for frame in frames
            ]

            for future in as_completed(futures):
                frame_path, hash_value = future.result()
                if hash_value is not None:
                    frame_hashes[frame_path] = hash_value
                progress.update(task, advance=1)

    # Deduplicate based on Hamming distance
    unique_frames = []
    unique_hashes = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task(
            "[cyan]Finding unique frames...", total=len(frame_hashes)
        )

        for frame_path, frame_hash in frame_hashes.items():
            is_unique = True

            # Compare with existing unique hashes
            for unique_hash in unique_hashes:
                hamming_dist = frame_hash - unique_hash
                if hamming_dist <= hamming_threshold:
                    is_unique = False
                    break

            if is_unique:
                unique_frames.append(frame_path)
                unique_hashes.append(frame_hash)

            progress.update(task, advance=1)

    console.print(
        f"[green]✓ Reduced from {len(frames)} to {len(unique_frames)} unique frames "
        f"({100 * (1 - len(unique_frames) / len(frames)):.1f}% reduction)[/green]"
    )

    return unique_frames


def filter_slide_frames(
    frames: List[Path],
    min_text_score: float = 0.3,
    edge_threshold: float = 50.0,
    workers: int = DEFAULT_WORKERS,
) -> List[Path]:
    """Filter frames to keep only slide-like frames.

    Args:
        frames: List of frame paths
        min_text_score: Minimum text density score
        edge_threshold: Edge density threshold
        workers: Number of parallel workers

    Returns:
        List of slide frame paths
    """
    console.print(
        f"\n[bold]Stage 3: Detecting slides from {len(frames)} frames...[/bold]"
    )

    slide_frames = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Detecting slide frames...", total=len(frames))

        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(check_frame_for_slide, frame, min_text_score, edge_threshold) 
                for frame in frames
            ]

            for future in as_completed(futures):
                frame_path, is_slide = future.result()
                if is_slide:
                    slide_frames.append(frame_path)
                progress.update(task, advance=1)

    # Sort frames by filename to maintain order
    slide_frames.sort()

    console.print(
        f"[green]✓ Detected {len(slide_frames)} slide frames "
        f"({100 * len(slide_frames) / len(frames):.1f}% are slides)[/green]"
    )

    return slide_frames


class VideoToSlidesConverter:
    """Converts video files to PDF slide decks with enhanced deduplication."""

    def __init__(self, config: Config):
        """Initialize converter with configuration.

        Args:
            config: Configuration object with processing parameters
        """
        self.config = config
        self.logger = self._setup_logging()
        self._setup_signal_handlers()
        self.state_file: Optional[Path] = None
        self.frames_dir: Optional[Path] = None

    def _setup_logging(self) -> logging.Logger:
        """Set up logging with both file and console handlers.

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger("video_to_slides_enhanced")
        logger.setLevel(logging.DEBUG if self.config.debug else logging.INFO)

        # Remove existing handlers
        logger.handlers.clear()

        # Console handler with Rich formatting
        console_handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            markup=True,  # Enable Rich markup processing
            show_path=False,  # Clean output
            show_time=True,
        )
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

        # File handler for debug logs
        if self.config.output_dir and not self.config.dry_run:
            log_path = self.config.output_dir / LOG_FILE
            file_handler = logging.FileHandler(log_path, mode="a")
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(funcName)s:%(lineno)d - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        return logger

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""

        def signal_handler(signum: int, frame) -> None:
            self.logger.info("\n[yellow]Interrupted! Cleaning up...[/yellow]")
            self._cleanup()
            sys.exit(1)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        atexit.register(self._cleanup)

    def _cleanup(self) -> None:
        """Clean up temporary directories and resources."""
        for temp_dir in temp_dirs:
            if temp_dir.exists():
                self.logger.debug(f"Cleaning up temporary directory: {temp_dir}")
                try:
                    import shutil

                    shutil.rmtree(temp_dir)
                except Exception as e:
                    self.logger.warning(f"Failed to clean up {temp_dir}: {e}")

    def check_dependencies(self) -> tuple[bool, Optional[str]]:
        """Check if all required system dependencies are available.

        Returns:
            (success, error_message) tuple
        """
        required_tools = {
            "ffmpeg": "Video processing tool. Install: https://ffmpeg.org/download.html",
            "ffprobe": "Part of ffmpeg. Install: https://ffmpeg.org/download.html",
            "gs": "Ghostscript for PDF compression. Install: https://ghostscript.com/download/",
        }

        missing_tools = []
        for tool, install_msg in required_tools.items():
            try:
                result = subprocess.run(
                    [tool, "-version"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode not in [0, 1]:
                    missing_tools.append(f"{tool}: {install_msg}")
                else:
                    self.logger.debug(f"Found {tool}: {result.stdout.splitlines()[0]}")
            except FileNotFoundError:
                missing_tools.append(f"{tool}: {install_msg}")

        if missing_tools:
            error_msg = "Missing required dependencies:\n" + "\n".join(
                f"  - {tool}" for tool in missing_tools
            )
            return False, error_msg

        # Check ffmpeg for mpdecimate filter
        result = subprocess.run(
            ["ffmpeg", "-filters"],
            capture_output=True,
            text=True,
            check=False,
        )
        if "mpdecimate" not in result.stdout:
            return (
                False,
                "FFmpeg does not have mpdecimate filter. Please install full ffmpeg.",
            )

        # Test required Python packages
        try:
            import ocrmypdf

            self.logger.debug(f"Found ocrmypdf Python API: {ocrmypdf.__version__}")
            # Test other imports without using them
            __import__("imagehash")
            __import__("cv2")
        except ImportError as e:
            return (
                False,
                f"Missing Python package: {e}. Install: pip install ocrmypdf imagehash opencv-python",
            )

        return True, None

    def save_state(self, state_data: dict) -> None:
        """Save processing state for resume capability.

        Args:
            state_data: Dictionary with current processing state
        """
        if self.config.dry_run or not self.state_file:
            return

        try:
            with open(self.state_file, "w") as f:
                json.dump(
                    {
                        **state_data,
                        "config": asdict(self.config),
                        "timestamp": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                    default=str,
                )
            self.logger.debug(f"Saved state to {self.state_file}")
        except Exception as e:
            self.logger.warning(f"Failed to save state: {e}")

    def load_state(self, state_file: Path) -> tuple[bool, Optional[dict]]:
        """Load processing state from file.

        Args:
            state_file: Path to state file

        Returns:
            (success, state_data) tuple
        """
        try:
            with open(state_file, "r") as f:
                state_data = json.load(f)
            self.logger.info(f"Loaded state from {state_file}")
            return True, state_data
        except Exception as e:
            return False, f"Failed to load state: {e}"

    def get_total_frames(self, video_path: Path, fps: float) -> int:
        """Get estimated total frames that will be extracted at given fps.
        
        Args:
            video_path: Path to video file
            fps: Target fps for extraction
            
        Returns:
            Estimated number of frames
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            return int(duration * fps)
        except (subprocess.CalledProcessError, ValueError, TypeError):
            # Fallback estimate
            return 1000

    def get_video_info(self, video_path: Path) -> tuple[bool, Optional[dict]]:
        """Get video information using ffprobe.

        Args:
            video_path: Path to video file

        Returns:
            (success, info_dict) tuple with duration, resolution, etc.
        """
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,duration,nb_frames,avg_frame_rate",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(video_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(result.stdout)

            # Extract relevant information
            stream = info.get("streams", [{}])[0]
            format_info = info.get("format", {})

            # Parse frame rate
            fps_str = stream.get("avg_frame_rate", "0/1")
            if "/" in fps_str:
                num, den = map(int, fps_str.split("/"))
                fps = num / den if den > 0 else 0
            else:
                fps = float(fps_str)

            # Try to get duration from format first, then stream as fallback
            duration = format_info.get("duration")
            if not duration:
                duration = stream.get("duration")
            duration = float(duration) if duration else 0.0
            
            video_info = {
                "width": int(stream.get("width", 0)),
                "height": int(stream.get("height", 0)),
                "duration": duration,
                "fps": fps,
                "nb_frames": int(stream.get("nb_frames", 0)),
            }

            return True, video_info
        except subprocess.CalledProcessError as e:
            return False, f"FFprobe failed: {e.stderr}"
        except Exception as e:
            return False, f"Failed to get video info: {e}"

    def extract_frames_ffmpeg(
        self, video_path: Path, output_dir: Path
    ) -> tuple[bool, Optional[list[Path]]]:
        """Extract unique frames using FFmpeg with mpdecimate.

        Args:
            video_path: Path to input video
            output_dir: Directory for output frames

        Returns:
            (success, frames_list) tuple
        """
        frames_dir = output_dir / "frames"
        frames_dir.mkdir(exist_ok=True, parents=True)
        self.frames_dir = frames_dir

        # Check available disk space
        import shutil
        free_space = shutil.disk_usage(frames_dir).free / (1024 * 1024 * 1024)  # GB
        if free_space < 1.0:  # Less than 1GB
            return False, f"Insufficient disk space: {free_space:.1f}GB available. Need at least 1GB for frame extraction."

        # Get video info for progress tracking
        success, video_info = self.get_video_info(video_path)
        if not success:
            self.logger.warning(f"Could not get video info: {video_info}")
            video_info = {"duration": 0, "fps": 30}

        duration = video_info.get("duration", 0)
        source_fps = video_info.get("fps", 30)
        
        # Estimate frames that will be extracted
        estimated_frames = int(duration * self.config.fps) if duration > 0 else 1000
        estimated_size_mb = estimated_frames * 0.5  # Rough estimate: 0.5MB per frame
        if estimated_size_mb > free_space * 1024:
            return False, f"Estimated output size ({estimated_size_mb:.0f}MB) exceeds available space ({free_space:.1f}GB)"

        # Get total frame count for progress calculation
        total_frames = self.get_total_frames(video_path, self.config.fps)
        
        # Construct optimized FFmpeg command 
        # Keep in yuv420p to avoid colorspace conversion, use JPG instead of PNG
        filter_str = (
            f"fps={self.config.fps},"
            "scale=1280:720:flags=fast_bilinear,"  # Fast scaling
            f"mpdecimate=hi={self.config.mpdecimate_hi}:"
            f"lo={self.config.mpdecimate_lo}:"
            f"frac={self.config.mpdecimate_frac},"
            "setpts=N/TB"
        )

        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-i",
            str(video_path),
            "-vf",
            filter_str,
            "-fps_mode",  # Use new option instead of deprecated -vsync
            "vfr",
            "-q:v",
            "3",  # Good quality JPEG (faster than PNG)
            "-pix_fmt", "yuv420p",  # Keep in native format
            "-loglevel", "info",  # Need info level for progress
            "-stats",  # Show progress stats
            "-progress", "pipe:2",  # Output progress to stderr
            "-threads",
            str(self.config.workers),
            str(frames_dir / "frame_%04d.jpg"),  # Use JPG instead of PNG
        ]

        console.print(
            f"[bold]Stage 1: Extracting frames at {self.config.fps} fps with mpdecimate[/bold]"
        )
        console.print(
            f"Settings: hi={self.config.mpdecimate_hi}, lo={self.config.mpdecimate_lo}, frac={self.config.mpdecimate_frac}"
        )

        if self.config.dry_run:
            console.print(f"[yellow]Dry run:[/yellow] Would execute: {' '.join(cmd)}")
            return True, []

        try:
            console.print(f"[cyan]Extracting frames with FFmpeg...[/cyan]")
            console.print(f"[dim]Available disk space: {free_space:.1f}GB[/dim]")
            console.print(f"[dim]Expected frames: {total_frames}, Size: {estimated_size_mb:.0f}MB[/dim]")
            
            # Run FFmpeg with proper progress tracking
            
            # Progress tracking variables
            progress_queue = queue.Queue()
            current_frame = 0
            
            def parse_progress(process, q):
                """Parse FFmpeg stderr output for progress info."""
                for line in iter(process.stderr.readline, ''):
                    if not line:
                        break
                    line = line.strip()
                    
                    # Look for frame=XXX in output
                    if line.startswith('frame='):
                        try:
                            frame_str = line.split()[0].split('=')[1]
                            frame_num = int(frame_str)
                            q.put(('frame', frame_num))
                        except (IndexError, ValueError):
                            pass
                    elif 'progress=' in line and 'end' in line:
                        q.put(('end', None))
                    elif self.config.debug and line:
                        q.put(('debug', line))
            
            # Start FFmpeg process
            process = subprocess.Popen(
                cmd, 
                stderr=subprocess.PIPE, 
                stdout=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Start progress parsing thread
            progress_thread = threading.Thread(target=parse_progress, args=(process, progress_queue))
            progress_thread.daemon = True
            progress_thread.start()
            
            # Show progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total} frames)"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Extracting frames...", 
                    total=total_frames,
                    completed=0
                )
                
                # Process progress updates
                while process.poll() is None:
                    try:
                        msg_type, value = progress_queue.get(timeout=0.1)
                        
                        if msg_type == 'frame':
                            current_frame = value
                            progress.update(task, completed=current_frame)
                        elif msg_type == 'end':
                            progress.update(task, completed=total_frames)
                            break
                        elif msg_type == 'debug' and self.config.debug:
                            console.print(f"[dim]FFmpeg: {value}[/dim]")
                            
                    except queue.Empty:
                        continue
                
                # Wait for process to finish
                process.wait()
                
                # Final update
                progress.update(task, completed=total_frames)
            
            if process.returncode != 0:
                return False, f"FFmpeg extraction failed with return code: {process.returncode}"

            # Get list of extracted frames (now JPG format)
            frames = sorted(frames_dir.glob("frame_*.jpg"))
            console.print(f"[green]✓ Extracted {len(frames)} frames from video[/green]")

            # Save state
            self.save_state({"step": "frames_extracted", "frames_count": len(frames)})

            return True, frames

        except Exception as e:
            return False, f"Frame extraction failed: {e}"

    def create_pdf_optimized(
        self, frames: list[Path], output_path: Path
    ) -> tuple[bool, Optional[str]]:
        """Create PDF from frames.

        Args:
            frames: List of frame paths
            output_path: Output PDF path

        Returns:
            (success, error_message) tuple
        """
        if not frames:
            return False, "No frames to create PDF"

        console.print()
        console.print(f"[bold]Creating PDF from {len(frames)} frames...[/bold]")

        if self.config.dry_run:
            console.print(
                f"[yellow]Dry run:[/yellow] Would create PDF at {output_path}"
            )
            return True, None

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:
                # Convert frames to RGB and create PDF
                pdf_task = progress.add_task("[cyan]Creating PDF...", total=len(frames))

                # Process frames in smaller chunks to avoid memory issues
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    converted_frames = []

                    for i, frame in enumerate(frames):
                        img = Image.open(frame)
                        if img.mode != "RGB":
                            img = img.convert("RGB")

                        # Save as JPEG for smaller size
                        temp_file = temp_path / f"temp_{i:04d}.jpg"
                        img.save(temp_file, "JPEG", quality=95, optimize=True)
                        converted_frames.append(temp_file)

                        progress.update(pdf_task, advance=1)

                    # Create PDF
                    with output_path.open("wb") as f:
                        f.write(img2pdf.convert([str(img) for img in converted_frames]))

            self.logger.info(
                f"[green]✓ Created PDF: {output_path} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)[/green]"
            )
            return True, None

        except Exception as e:
            return False, f"PDF creation failed: {e}"

    def ocr_pdf_clean(
        self, input_pdf: Path, output_pdf: Path
    ) -> tuple[bool, Optional[str]]:
        """OCR the PDF with clean output (no spam).

        Args:
            input_pdf: Input PDF path
            output_pdf: Output OCR'd PDF path

        Returns:
            (success, error_message) tuple
        """
        if self.config.skip_ocr:
            self.logger.info("[yellow]Skipping OCR step (--no-ocr flag set)[/yellow]")
            return True, None

        console.print()
        console.print("[bold]Running OCR to make PDF searchable...[/bold]")

        if self.config.dry_run:
            console.print(
                f"[yellow]Dry run:[/yellow] Would OCR {input_pdf} to {output_pdf}"
            )
            return True, None

        try:
            # Configure OCR options
            ocr_options = {
                "rotate_pages": True,
                "deskew": True,
                "clean": True,
                "optimize": 3,
                "jobs": self.config.workers,
                "progress_bar": False,
            }

            # Suppress ocrmypdf logging to avoid spam
            ocrmypdf.configure_logging(verbosity=-1)  # Suppress all output
            
            # Add tesseract options to suppress errors
            ocr_options["tesseract_config"] = []
            ocr_options["tesseract_non_ocr_strategy"] = "skip"  # Skip pages that don't need OCR

            # Create a custom progress display
            with Live(
                "[cyan]Processing OCR... Please wait[/cyan]",
                console=console,
                refresh_per_second=1,
            ) as live:
                # Redirect stderr to suppress tesseract errors
                old_stderr = sys.stderr
                sys.stderr = io.StringIO()
                
                try:
                    # Run OCR using Python API
                    ocrmypdf.ocr(str(input_pdf), str(output_pdf), **ocr_options)
                    live.update("[green]✓ OCR completed successfully[/green]")
                finally:
                    # Restore stderr
                    sys.stderr = old_stderr

            self.logger.info(
                f"[green]✓ Created OCR PDF: {output_pdf} ({output_pdf.stat().st_size / 1024 / 1024:.1f} MB)[/green]"
            )
            return True, None

        except Exception as e:
            return False, f"OCR failed: {e}"

    def compress_pdf(
        self, input_pdf: Path, output_pdf: Path
    ) -> tuple[bool, Optional[str]]:
        """Lightly compress PDF using ghostscript.

        Args:
            input_pdf: Input PDF path
            output_pdf: Output compressed PDF path

        Returns:
            (success, error_message) tuple
        """
        if self.config.skip_compress:
            self.logger.info(
                "[yellow]Skipping compression step (--no-compress flag set)[/yellow]"
            )
            return True, None

        console.print()
        console.print("[bold]Compressing PDF...[/bold]")

        if self.config.dry_run:
            console.print(
                f"[yellow]Dry run:[/yellow] Would compress {input_pdf} to {output_pdf}"
            )
            return True, None

        cmd = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/prepress",  # 300 DPI, good quality
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-dNumRenderingThreads={self.config.workers}",
            f"-sOutputFile={output_pdf}",
            str(input_pdf),
        ]

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Compressing PDF...", total=None)

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                progress.update(task, completed=100)

            if result.returncode != 0:
                self.logger.debug(f"Compression stderr: {result.stderr}")
                return False, f"Compression failed: {result.stderr}"

            # Calculate compression ratio
            original_size = input_pdf.stat().st_size / 1024 / 1024
            compressed_size = output_pdf.stat().st_size / 1024 / 1024
            ratio = (
                (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            )

            self.logger.info(
                f"[green]✓ Compressed PDF: {output_pdf} "
                f"({compressed_size:.1f} MB, {ratio:.0f}% reduction)[/green]"
            )
            return True, None

        except Exception as e:
            return False, f"Compression failed: {e}"

    def process_video(self) -> tuple[bool, Optional[str]]:
        """Main processing pipeline with multi-stage deduplication.

        Returns:
            (success, error_message) tuple
        """
        if not self.config.video_path or not self.config.video_path.exists():
            return False, f"Video file not found: {self.config.video_path}"

        # Create output directory
        if not self.config.output_dir:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            self.config.output_dir = Path(f"video_slides_{timestamp}")

        self.config.output_dir.mkdir(exist_ok=True, parents=True)
        self.state_file = self.config.output_dir / STATE_FILE

        # Re-setup logging now that we have output directory
        self.logger = self._setup_logging()

        # Use console.print for Rich formatting instead of logger
        console.print()
        console.print(
            "[bold cyan]Video to Slides Converter (Enhanced Multi-Stage Pipeline)[/bold cyan]"
        )
        console.print(f"Video: {self.config.video_path.name}")
        console.print(f"Output: {self.config.output_dir}")
        console.print(f"Workers: {self.config.workers}")
        console.print()

        # Check if resuming
        if self.config.resume_state:
            self.logger.info(
                f"[yellow]Resuming from step: {self.config.resume_state.get('step')}[/yellow]"
            )

        # Step 1: Extract frames with FFmpeg + mpdecimate
        frames = []
        if self.config.resume_state.get("step") in [
            "frames_extracted",
            "frames_deduped",
            "slides_filtered",
            "pdf_created",
            "ocr_done",
            "completed",
        ]:
            # Skip extraction if already done
            frames_dir = self.config.output_dir / "frames"
            if frames_dir.exists():
                frames = sorted(frames_dir.glob("frame_*.jpg"))
                self.logger.info(
                    f"[yellow]Found {len(frames)} existing frames[/yellow]"
                )
        else:
            success, result = self.extract_frames_ffmpeg(
                self.config.video_path, self.config.output_dir
            )
            if not success:
                return False, result
            frames = result

        if not frames:
            return False, "No frames extracted"

        # Step 2: Deduplicate with dhash
        if self.config.resume_state.get("step") not in [
            "frames_deduped",
            "slides_filtered",
            "pdf_created",
            "ocr_done",
            "completed",
        ]:
            frames = deduplicate_with_dhash(
                frames,
                self.config.hamming_threshold,
                self.config.dhash_size,
                self.config.workers,
            )
            self.save_state({"step": "frames_deduped", "frames_count": len(frames)})

        # Step 3: Filter to keep only slide frames
        if self.config.resume_state.get("step") not in [
            "slides_filtered",
            "pdf_created",
            "ocr_done",
            "completed",
        ]:
            frames = filter_slide_frames(
                frames,
                self.config.min_text_score,
                self.config.edge_threshold,
                self.config.workers,
            )
            self.save_state({"step": "slides_filtered", "frames_count": len(frames)})

        # Log final frame count
        console.print()
        console.print(
            f"[bold green]Final result: {len(frames)} slide frames ready for PDF[/bold green]"
        )

        # Prepare output filenames
        video_stem = self.config.video_path.stem
        pdf_path = self.config.output_dir / f"{video_stem}.pdf"
        ocr_pdf_path = self.config.output_dir / f"{video_stem}_ocr.pdf"
        compressed_pdf_path = self.config.output_dir / f"{video_stem}_compressed.pdf"

        # Step 4: Create PDF
        if not pdf_path.exists() or self.config.resume_state.get("step") not in [
            "pdf_created",
            "ocr_done",
            "completed",
        ]:
            success, error = self.create_pdf_optimized(frames, pdf_path)
            if not success:
                return False, error
            self.save_state({"step": "pdf_created"})

        # Step 5: OCR PDF with clean output
        if not self.config.skip_ocr and (
            not ocr_pdf_path.exists()
            or self.config.resume_state.get("step") not in ["ocr_done", "completed"]
        ):
            success, error = self.ocr_pdf_clean(pdf_path, ocr_pdf_path)
            if not success:
                self.logger.warning(f"OCR failed: {error}")
                # Continue anyway, OCR is not critical
            else:
                self.save_state({"step": "ocr_done"})

        # Step 6: Compress PDF
        final_pdf = ocr_pdf_path if ocr_pdf_path.exists() else pdf_path
        if not self.config.skip_compress and not compressed_pdf_path.exists():
            success, error = self.compress_pdf(final_pdf, compressed_pdf_path)
            if not success:
                self.logger.warning(f"Compression failed: {error}")
                # Continue anyway, compression is not critical

        # Save final state
        self.save_state({"step": "completed"})

        # Print summary
        self._print_summary()

        return True, None

    def _print_summary(self) -> None:
        """Print processing summary table."""
        table = Table(title="Processing Summary", show_header=True)
        table.add_column("File", style="cyan")
        table.add_column("Size", justify="right", style="green")

        # List all PDFs created
        for pdf_file in sorted(self.config.output_dir.glob("*.pdf")):
            size_mb = pdf_file.stat().st_size / 1024 / 1024
            table.add_row(pdf_file.name, f"{size_mb:.1f} MB")

        console.print("\n", table, "\n")
        console.print(
            f"[bold green]✓ Processing complete![/bold green] "
            f"Output directory: {self.config.output_dir}"
        )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Extract unique frames from video and create PDF slide deck (Enhanced Multi-Stage)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Multi-Stage Deduplication Pipeline:
  1. FFmpeg extraction at 1fps with mpdecimate
  2. Perceptual hash-based deduplication (dhash)
  3. Content-based slide detection (remove video-like frames)

Examples:
  # Basic usage
  %(prog)s video.mp4

  # Aggressive deduplication for presentations
  %(prog)s presentation.mp4 --mpdecimate-hi 2048 --hamming-threshold 15

  # Less aggressive for videos with animations
  %(prog)s lecture.mp4 --mpdecimate-hi 1024 --hamming-threshold 5

  # Skip OCR and compression
  %(prog)s video.mp4 --no-ocr --no-compress

  # Debug mode with dry run
  %(prog)s video.mp4 --debug --dry-run

Expected Results:
  - Presentation videos: ~200 slides from 60min video
  - Reduces 900+ frames to manageable slide count
  - Clean OCR output without spam

Note: Requires ffmpeg, ocrmypdf, ghostscript, and opencv-python.
        """,
    )

    # Required arguments
    parser.add_argument(
        "video",
        nargs="?",
        type=Path,
        help="Path to input video file",
    )

    # Optional arguments
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        help="Output directory (default: video_slides_TIMESTAMP)",
    )

    # Frame extraction options
    parser.add_argument(
        "--fps",
        type=float,
        default=DEFAULT_FPS,
        help=f"Frames per second to extract (default: {DEFAULT_FPS})",
    )

    # MPDecimate options
    parser.add_argument(
        "--mpdecimate-hi",
        type=int,
        default=DEFAULT_MPDECIMATE_HI,
        help=f"MPDecimate high threshold (default: {DEFAULT_MPDECIMATE_HI})",
    )

    parser.add_argument(
        "--mpdecimate-lo",
        type=int,
        default=DEFAULT_MPDECIMATE_LO,
        help=f"MPDecimate low threshold (default: {DEFAULT_MPDECIMATE_LO})",
    )

    parser.add_argument(
        "--mpdecimate-frac",
        type=float,
        default=DEFAULT_MPDECIMATE_FRAC,
        help=f"MPDecimate fraction threshold (default: {DEFAULT_MPDECIMATE_FRAC})",
    )

    # Deduplication options
    parser.add_argument(
        "--dhash-size",
        type=int,
        default=DHASH_SIZE,
        help=f"Size of dhash for deduplication (default: {DHASH_SIZE})",
    )

    parser.add_argument(
        "--hamming-threshold",
        type=int,
        default=HAMMING_THRESHOLD,
        help=f"Hamming distance threshold for similarity (default: {HAMMING_THRESHOLD})",
    )

    # Slide detection options
    parser.add_argument(
        "--min-text-score",
        type=float,
        default=0.3,
        help="Minimum text density score for slide detection (default: 0.3)",
    )

    parser.add_argument(
        "--edge-threshold",
        type=float,
        default=50.0,
        help="Edge density threshold for slide detection (default: 50.0)",
    )

    # Processing options
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Skip OCR step",
    )

    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Skip compression step",
    )

    # Performance options
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of parallel workers (default: {DEFAULT_WORKERS})",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Batch size for frame processing (default: {BATCH_SIZE})",
    )

    # Required flags per CLAUDE.md
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help="Resume from state file or load config",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Required for multiprocessing on Windows/macOS
    if __name__ != "__main__":
        return 1

    args = parse_arguments()

    # Create config from arguments
    config = Config(
        fps=args.fps,
        mpdecimate_hi=args.mpdecimate_hi,
        mpdecimate_lo=args.mpdecimate_lo,
        mpdecimate_frac=args.mpdecimate_frac,
        skip_ocr=args.no_ocr,
        skip_compress=args.no_compress,
        dry_run=args.dry_run,
        debug=args.debug,
        output_dir=args.output_dir,
        workers=args.workers,
        batch_size=args.batch_size,
        dhash_size=args.dhash_size,
        hamming_threshold=args.hamming_threshold,
        min_text_score=args.min_text_score,
        edge_threshold=args.edge_threshold,
    )

    # Handle config file / resume
    if args.config:
        if not args.config.exists():
            console.print(f"[red]Error: Config file not found: {args.config}[/red]")
            return 1

        # Load state
        converter = VideoToSlidesConverter(config)
        success, state = converter.load_state(args.config)
        if not success:
            console.print(f"[red]Error: {state}[/red]")
            return 1

        # Update config from state
        if "config" in state:
            for key, value in state["config"].items():
                if hasattr(config, key) and key != "resume_state":
                    if key in ["output_dir", "video_path", "config_file"]:
                        value = Path(value) if value else None
                    setattr(config, key, value)

        config.resume_state = state

        # Set output directory from state file location
        if not config.output_dir:
            config.output_dir = args.config.parent

    else:
        # Normal mode - require video argument
        if not args.video:
            console.print(
                "[red]Error: Video path required (unless using --config)[/red]"
            )
            console.print("Use --help for usage information")
            return 1

        config.video_path = args.video

    # Create converter and check dependencies
    converter = VideoToSlidesConverter(config)
    success, error = converter.check_dependencies()
    if not success:
        console.print(f"[red]Error: {error}[/red]")
        return 1

    # Process video
    success, error = converter.process_video()
    if not success:
        console.print(f"[red]Error: {error}[/red]")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
