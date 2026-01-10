#!/usr/bin/env python3
"""
Fireflies Transcription CLI - Upload audio, get transcript and summary
Robust CLI tool for processing audio files through Fireflies API
"""

import os
import sys
import json
import time
import argparse
import logging
import logging.handlers
import signal
import atexit
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import requests
from dataclasses import dataclass, asdict
import hashlib
import uuid
try:
    from mutagen import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


def setup_logging(debug: bool = False, log_dir: Optional[Path] = None) -> logging.Logger:
    """Setup robust logging with file and console handlers"""
    logger = logging.getLogger('fireflies_cli')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler - cleaner format for user
    console_handler = logging.StreamHandler(sys.stdout)
    console_level = logging.DEBUG if debug else logging.INFO
    console_handler.setLevel(console_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler - detailed format with rotation
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f'fireflies_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        # Rotating file handler (10MB max, keep 5 backups)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Always detailed in file
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
        
        # Also create a JSON log for machine processing
        json_log_file = log_dir / f'fireflies_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        json_handler = logging.FileHandler(json_log_file, encoding='utf-8')
        json_handler.setLevel(logging.DEBUG)
        
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_obj = {
                    'timestamp': datetime.now().isoformat(),
                    'level': record.levelname,
                    'function': record.funcName,
                    'line': record.lineno,
                    'message': record.getMessage(),
                    'module': record.module
                }
                if hasattr(record, 'audio_file'):
                    log_obj['audio_file'] = record.audio_file
                if hasattr(record, 'error'):
                    log_obj['error'] = str(record.error)
                return json.dumps(log_obj)
        
        json_handler.setFormatter(JSONFormatter())
        logger.addHandler(json_handler)
        
        logger.info(f"📝 Logging to: {log_file}")
        logger.info(f"📊 JSON log: {json_log_file}")
    
    return logger


# Initialize logger (will be reconfigured in main)
logger = setup_logging()


@dataclass
class ProcessingResult:
    """Result of processing an audio file"""
    success: bool
    audio_file: str
    base_name: str
    transcript_id: Optional[str] = None
    word_count: int = 0
    duration_seconds: int = 0
    has_summary: bool = False
    error_message: Optional[str] = None
    processing_time_seconds: int = 0
    output_files: list = None

    def __post_init__(self):
        if self.output_files is None:
            self.output_files = []


class FirefliesTranscriber:
    """Main transcriber class with retry logic and error handling"""
    
    def __init__(self, api_key: str, output_dir: Optional[Path] = None, debug: bool = False):
        self.api_key = api_key
        self.output_dir = output_dir  # If None, outputs go next to input file
        self.debug = debug
        
        # API endpoints
        self.fireflies_api = 'https://api.fireflies.ai/graphql'
        self.tmpfiles_api = 'https://tmpfiles.org/api/v1/upload'
        
        # Session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
        
        # State tracking
        self.current_task = None
        
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        atexit.register(self._cleanup)
    
    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info("Received shutdown signal, cleaning up...")
        self._cleanup()
        sys.exit(0)
    
    def _cleanup(self):
        """Cleanup on exit"""
        if self.current_task and 'temp_files' in self.current_task:
            for temp_file in self.current_task['temp_files']:
                try:
                    if Path(temp_file).exists():
                        Path(temp_file).unlink()
                        logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    logger.debug(f"Failed to cleanup {temp_file}: {e}")
    
    def _atomic_write(self, content: str, target_path: Path) -> bool:
        """Write content atomically using temp file and rename"""
        temp_fd = None
        temp_path = None
        try:
            # Create temp file in same directory as target
            temp_fd, temp_path = tempfile.mkstemp(
                dir=target_path.parent,
                prefix=f".{target_path.name}.",
                suffix='.tmp'
            )
            
            # Write content
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            temp_fd = None  # Mark as closed
            
            # Atomic rename
            Path(temp_path).replace(target_path)
            logger.debug(f"Atomically wrote {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write {target_path}: {e}")
            if temp_fd is not None:
                os.close(temp_fd)
            if temp_path and Path(temp_path).exists():
                Path(temp_path).unlink()
            return False
    
    def _retry_with_backoff(self, func, max_attempts: int = 3, initial_delay: float = 1.0):
        """Execute function with exponential backoff retry"""
        delay = initial_delay
        for attempt in range(max_attempts):
            try:
                result = func()
                if result is not None:
                    return result
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                delay = min(delay * 2, 60)  # Cap at 60 seconds
        return None
    
    def get_audio_duration(self, audio_path: Path) -> Optional[float]:
        """Get actual audio file duration in seconds using mutagen"""
        if not MUTAGEN_AVAILABLE:
            logger.debug("Mutagen not available, skipping duration check")
            return None
        
        try:
            audio_file = MutagenFile(str(audio_path))
            if audio_file and hasattr(audio_file.info, 'length'):
                duration = audio_file.info.length
                logger.debug(f"Audio duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
                return duration
            else:
                logger.warning("Could not extract duration from audio file")
                return None
        except Exception as e:
            logger.warning(f"Error getting audio duration: {e}")
            return None
    
    def upload_to_tmpfiles(self, audio_path: Path) -> Optional[str]:
        """Upload audio file to tmpfiles.org for temporary hosting"""
        logger.info(f"📤 Uploading {audio_path.name} to temporary hosting...")
        
        file_size_mb = audio_path.stat().st_size / 1024 / 1024
        logger.info(f"  File size: {file_size_mb:.2f} MB")
        
        def _upload():
            with open(audio_path, 'rb') as f:
                # Detect mime type based on extension
                mime_type = 'audio/mpeg'
                if audio_path.suffix.lower() == '.opus':
                    mime_type = 'audio/opus'
                elif audio_path.suffix.lower() == '.wav':
                    mime_type = 'audio/wav'
                elif audio_path.suffix.lower() == '.m4a':
                    mime_type = 'audio/m4a'
                
                files = {'file': (audio_path.name, f, mime_type)}
                response = requests.post(
                    self.tmpfiles_api, 
                    files=files,
                    timeout=300
                )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    url = data['data']['url']
                    # Convert to download URL and ensure HTTPS
                    download_url = url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')
                    download_url = download_url.replace('http://', 'https://')
                    logger.info(f"  ✅ Upload successful: {download_url}")
                    return download_url
            
            logger.error(f"  Upload failed: HTTP {response.status_code}")
            return None
        
        return self._retry_with_backoff(_upload)
    
    def submit_to_fireflies(self, audio_url: str, title: str, reference_id: str) -> bool:
        """Submit audio URL to Fireflies for processing"""
        logger.info(f"🚀 Submitting to Fireflies: {title}")
        
        mutation = """
        mutation($input: AudioUploadInput) {
            uploadAudio(input: $input) {
                success
                title
                message
            }
        }
        """
        
        variables = {
            "input": {
                "url": audio_url,
                "title": title,
                "client_reference_id": reference_id
            }
        }
        
        def _submit():
            response = self.session.post(
                self.fireflies_api,
                json={'query': mutation, 'variables': variables},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and data.get('data', {}).get('uploadAudio', {}).get('success'):
                    logger.info("  ✅ Submitted successfully")
                    return True
                else:
                    error_msg = data.get('errors', [{}])[0].get('message', 'Unknown error') if data else 'No response'
                    logger.error(f"  ❌ Submission failed: {error_msg}")
            else:
                logger.error(f"  ❌ HTTP {response.status_code}")
            return False
        
        return self._retry_with_backoff(_submit)
    
    def wait_for_transcript(self, title: str, max_wait_minutes: int = 30) -> Optional[str]:
        """Poll for transcript completion"""
        logger.info(f"⏳ Waiting for transcription to complete...")
        
        start_time = datetime.now()
        check_interval = 30  # seconds
        check_count = 0
        
        query = """
        query($limit: Int) {
            transcripts(limit: $limit) {
                id
                title
                duration
                date
            }
        }
        """
        
        while (datetime.now() - start_time).total_seconds() < max_wait_minutes * 60:
            check_count += 1
            
            try:
                response = self.session.post(
                    self.fireflies_api,
                    json={'query': query, 'variables': {'limit': 20}},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    transcripts = data.get('data', {}).get('transcripts', [])
                    
                    # Look for our transcript
                    for t in transcripts:
                        if title.lower() in t.get('title', '').lower():
                            if t.get('duration'):  # Ready when duration is set
                                logger.info(f"  ✅ Transcript ready! ID: {t['id']}")
                                return t['id']
                            else:
                                logger.info(f"  ⏳ Found but still processing...")
            
            except Exception as e:
                logger.warning(f"  Check #{check_count} failed: {e}")
            
            elapsed = int((datetime.now() - start_time).total_seconds())
            remaining = max_wait_minutes * 60 - elapsed
            logger.info(f"  Check #{check_count}: Not ready. Elapsed: {elapsed}s, Remaining: {remaining}s")
            
            if remaining > check_interval:
                time.sleep(check_interval)
            else:
                break
        
        logger.error(f"  ❌ Timeout after {max_wait_minutes} minutes")
        return None
    
    def download_transcript(self, transcript_id: str, wait_for_overview: bool = True, checking_overview: bool = False) -> Optional[Dict[str, Any]]:
        """Download full transcript and wait for overview if requested"""
        if checking_overview:
            logger.info(f"🔍 Checking for overview availability...")
        else:
            logger.info(f"📥 Downloading transcript {transcript_id}...")
        
        query = """
        query($transcriptId: String!) {
            transcript(id: $transcriptId) {
                id
                title
                duration
                date
                sentences {
                    text
                    speaker_name
                    start_time
                    end_time
                }
                summary {
                    keywords
                    overview
                    action_items
                    bullet_gist
                    shorthand_bullet
                    outline
                }
            }
        }
        """
        
        # First download attempt
        response = self.session.post(
            self.fireflies_api,
            json={'query': query, 'variables': {'transcriptId': transcript_id}},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            transcript = data.get('data', {}).get('transcript')
            
            if transcript:
                sentences = transcript.get('sentences', [])
                word_count = sum(len(s.get('text', '').split()) for s in sentences) if sentences else 0
                
                has_summary = bool(transcript.get('summary') and 
                                 transcript['summary'].get('overview'))
                
                logger.info(f"  ✅ Downloaded: {word_count} words, summary: {has_summary}")
                
                # If no summary yet but we want to wait for it
                if not has_summary and wait_for_overview:
                    logger.info("  ⏳ Summary not ready yet, waiting...")
                    
                    # Poll for summary (up to 5 minutes)
                    max_summary_wait = 5 * 60  # 5 minutes
                    check_interval = 30  # 30 seconds
                    elapsed = 0
                    
                    while elapsed < max_summary_wait:
                        time.sleep(check_interval)
                        elapsed += check_interval
                        
                        # Try again
                        response = self.session.post(
                            self.fireflies_api,
                            json={'query': query, 'variables': {'transcriptId': transcript_id}},
                            timeout=60
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            transcript = data.get('data', {}).get('transcript')
                            
                            if transcript:
                                has_summary = bool(transcript.get('summary') and 
                                                 transcript['summary'].get('overview'))
                                
                                if has_summary:
                                    logger.info(f"  ✅ Summary ready after {elapsed}s wait!")
                                    return transcript
                                else:
                                    logger.info(f"  ⏳ Still waiting for summary... ({elapsed}s elapsed)")
                    
                    logger.warning(f"  ⚠️  Summary not available after {max_summary_wait}s wait")
                
                return transcript
            else:
                logger.error("  ❌ No transcript data in response")
        else:
            logger.error(f"  ❌ HTTP {response.status_code}")
        
        return None
    
    def delete_transcript(self, transcript_id: str, wait_for_deletion: bool = False, check_interval: int = 30) -> bool:
        """Delete transcript from Fireflies (works with eventual consistency)"""
        logger.info(f"🗑️  Deleting transcript {transcript_id} from Fireflies...")
        
        # IMPORTANT: deleteTranscript DOES work but with eventual consistency.
        # The deletion is asynchronous - the API returns immediately with the
        # transcript data, but the actual deletion happens in the background.
        # It may take 5-15 minutes for the transcript to disappear from queries.
        mutation = """
        mutation($transcriptId: String!) {
            deleteTranscript(id: $transcriptId) {
                title
                date
                duration
                organizer_email
            }
        }
        """
        
        def _delete():
            try:
                response = self.session.post(
                    self.fireflies_api,
                    json={'query': mutation, 'variables': {'transcriptId': transcript_id}},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"Delete response: {json.dumps(data)}")
                    
                    if data and not data.get('errors'):
                        deleted_transcript = data.get('data', {}).get('deleteTranscript')
                        if deleted_transcript:
                            logger.info(f"  ✅ Deletion initiated for '{deleted_transcript.get('title', 'Unknown')}'")
                            logger.info(f"  ⏱️  Note: Deletion is async - may take 5-15 minutes to complete")
                            return True
                    else:
                        errors = data.get('errors', [])
                        if errors:
                            error_msg = errors[0].get('message', 'Unknown error')
                            error_code = errors[0].get('extensions', {}).get('code', '')
                            
                            if 'require_elevated_privilege' in error_msg or error_code == 'require_elevated_privilege':
                                logger.warning(f"  ⚠️  Deletion requires admin privileges (current API key lacks permission)")
                            else:
                                logger.warning(f"  ⚠️  GraphQL error: {error_msg}")
                else:
                    logger.warning(f"  ⚠️  HTTP {response.status_code}: {response.text[:200]}")
                    
            except Exception as e:
                logger.warning(f"  ⚠️  Exception during deletion: {e}")
            
            return False
        
        # Try to delete with minimal retries
        success = self._retry_with_backoff(_delete, max_attempts=1)
        if not success:
            logger.info("  ℹ️  Deletion request failed")
            return False
        
        # If requested, wait for deletion to complete
        if wait_for_deletion and success:
            logger.info("  ⏳ Waiting for deletion to complete (may take up to 15 minutes)...")
            
            max_wait_minutes = 15
            # Use provided check interval
            elapsed = 0
            
            query = """
            query($transcriptId: String!) {
                transcript(id: $transcriptId) {
                    id
                    title
                }
            }
            """
            
            while elapsed < max_wait_minutes * 60:
                time.sleep(check_interval)
                elapsed += check_interval
                
                # Check if transcript still exists
                try:
                    response = self.session.post(
                        self.fireflies_api,
                        json={'query': query, 'variables': {'transcriptId': transcript_id}},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        transcript = data.get('data', {}).get('transcript')
                        
                        if transcript is None:
                            logger.info(f"  ✅ Deletion confirmed after {elapsed}s - transcript no longer exists!")
                            return True
                        else:
                            remaining = (max_wait_minutes * 60) - elapsed
                            logger.info(f"  ⏳ Waiting for deletion... ({elapsed}s elapsed, {remaining}s remaining)")
                    
                except Exception as e:
                    logger.debug(f"Error checking deletion status: {e}")
            
            # Timeout - but deletion may still complete later
            logger.warning(f"  ⚠️  Deletion not confirmed after {max_wait_minutes} minutes")
            logger.info("  ℹ️  Deletion may still complete - check manually later")
        
        return success
    
    def save_transcript_files(self, transcript: Dict[str, Any], audio_path: Path, force: bool = False) -> list:
        """Save transcript files immediately when available"""
        logger.info("💾 Saving transcript files...")
        
        output_files = []
        temp_files = []
        
        # Validate transcript duration matches audio file
        fireflies_duration_min = transcript.get('duration', 0)  # In minutes
        actual_duration_sec = self.get_audio_duration(audio_path)
        
        if fireflies_duration_min and actual_duration_sec:
            fireflies_duration_sec = fireflies_duration_min * 60
            duration_diff = abs(fireflies_duration_sec - actual_duration_sec)
            duration_diff_percent = (duration_diff / actual_duration_sec) * 100
            
            logger.info(f"  🎵 Audio file duration: {actual_duration_sec:.1f}s ({actual_duration_sec/60:.2f} min)")
            logger.info(f"  📝 Fireflies duration: {fireflies_duration_sec:.1f}s ({fireflies_duration_min:.2f} min)")
            
            # Allow 2 seconds tolerance for rounding differences
            if duration_diff <= 2:
                logger.info(f"  ✅ Duration validation passed (within 2s tolerance)")
            # Warn if difference is more than 10 seconds AND more than 5%
            elif duration_diff > 10 and duration_diff_percent > 5:
                logger.warning(f"  ⚠️  DURATION MISMATCH: {duration_diff:.1f}s difference ({duration_diff_percent:.1f}%)")
                logger.warning(f"     Fireflies may have only processed part of the audio!")
                
                # Critical error if less than 50% was processed
                if fireflies_duration_sec < (actual_duration_sec * 0.5):
                    logger.error(f"  ❌ CRITICAL: Less than 50% of audio was transcribed!")
                    logger.error(f"     Consider re-uploading the file or checking Fireflies limits")
            else:
                logger.info(f"  ✅ Duration validation passed ({duration_diff:.1f}s difference)")
        
        # Determine output directory and base name
        if self.output_dir:
            output_base_dir = self.output_dir
            output_base_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_base_dir = audio_path.parent
        
        # Base filename with extension (e.g., "audio.opus")
        base_name = audio_path.name
        
        # Track temp files for cleanup
        if self.current_task:
            self.current_task['temp_files'] = temp_files
        
        # Helper to check if file exists and handle force flag
        def should_write(file_path: Path) -> bool:
            if not file_path.exists():
                return True
            if force:
                logger.info(f"  ⚠️  Overwriting existing file: {file_path.name}")
                return True
            logger.warning(f"  ⏭️  Skipping existing file: {file_path.name} (use --force to overwrite)")
            return False
        
        # 1. Save full transcript JSON
        transcript_json_file = output_base_dir / f"{base_name}.transcript.json"
        if should_write(transcript_json_file):
            content = json.dumps(transcript, indent=2)
            if self._atomic_write(content, transcript_json_file):
                output_files.append(str(transcript_json_file))
                logger.info(f"  ✅ {transcript_json_file.name}")
        
        # 2. Save transcript as plain text (Fireflies style)
        transcript_txt_file = output_base_dir / f"{base_name}.transcript.txt"
        if should_write(transcript_txt_file):
            sentences = transcript.get('sentences') or []  # Handle null sentences
            lines = []
            
            # Add title and duration at the top
            lines.append(transcript.get('title', audio_path.stem))
            
            # Add transcript ID if available
            if transcript.get('id'):
                lines.append(f"Transcript ID: {transcript['id']}")
            
            # Add duration (value is in minutes, convert to MM:SS format)
            duration = transcript.get('duration', 0)
            if duration:
                # Duration is in minutes, convert to total seconds first
                total_seconds = int(duration * 60)
                mins = total_seconds // 60
                secs = total_seconds % 60
                lines.append(f"Duration: {mins:02d}:{secs:02d}")
            lines.append("")
            
            current_speaker = None
            
            # Check if we have any content
            if not sentences:
                lines.append("")
                lines.append("⚠️ No transcript content available")
                lines.append("This may be due to:")
                lines.append("- Audio file shorter than 2 minutes (Fireflies limitation)")
                lines.append("- Processing error on Fireflies side")
                lines.append("- Corrupted or unsupported audio format")
            
            for s in sentences:
                text = s.get('text', '').strip()
                speaker = s.get('speaker_name') or 'Speaker'
                
                if text:
                    # Add speaker label when speaker changes
                    if speaker != current_speaker:
                        if lines:  # Add blank line between speakers
                            lines.append("")
                        lines.append(f"{speaker}:")
                        current_speaker = speaker
                    
                    # Add the text with timestamp
                    start_time = s.get('start_time', 0)
                    # Fireflies always sends timestamps in seconds, not milliseconds
                    mins = int(start_time // 60)
                    secs = int(start_time % 60)
                    lines.append(f"[{mins:02d}:{secs:02d}] {text}")
            
            content = '\n'.join(lines)
            if self._atomic_write(content, transcript_txt_file):
                output_files.append(str(transcript_txt_file))
                logger.info(f"  ✅ {transcript_txt_file.name}")
        
        # 3. Save transcript as Markdown with timestamps
        transcript_md_file = output_base_dir / f"{base_name}.transcript.md"
        if should_write(transcript_md_file):
            lines = []
            lines.append(f"# {transcript.get('title', audio_path.stem)}")
            lines.append("")
            # Format date properly - if it's a timestamp, convert it
            date_val = transcript.get('date', datetime.now())
            if isinstance(date_val, (int, float)):
                # It's a timestamp, convert to datetime
                date_str = datetime.fromtimestamp(date_val / 1000 if date_val > 1e10 else date_val).strftime('%B %d, %Y, %I:%M %p PDT')
            elif isinstance(date_val, str):
                date_str = date_val
            else:
                date_str = datetime.now().strftime('%B %d, %Y, %I:%M %p PDT')
            lines.append(date_str)
            
            # Add transcript ID if available
            if transcript.get('id'):
                lines.append(f"**Transcript ID:** {transcript['id']}")
            
            # Add duration (value is in minutes, convert to MM:SS format)
            duration = transcript.get('duration', 0)
            if duration:
                # Duration is in minutes, convert to total seconds first
                total_seconds = int(duration * 60)
                mins = total_seconds // 60
                secs = total_seconds % 60
                lines.append(f"**Duration:** {mins:02d}:{secs:02d}")
            
            lines.append("")
            lines.append("## Transcript")
            lines.append("")
            
            # Group sentences by speaker for cleaner formatting
            sentences = transcript.get('sentences') or []  # Handle null sentences
            current_speaker = None
            speaker_block = []
            
            # Check if we have any content
            if not sentences:
                lines.append("⚠️ **No transcript content available**")
                lines.append("")
                lines.append("This may be due to:")
                lines.append("- Audio file shorter than 2 minutes (Fireflies limitation)")
                lines.append("- Processing error on Fireflies side")
                lines.append("- Corrupted or unsupported audio format")
            
            for s in sentences:
                text = s.get('text', '').strip()
                speaker = s.get('speaker_name') or 'Speaker'
                
                if text:
                    start_time = s.get('start_time', 0)
                    # Fireflies always sends timestamps in seconds, not milliseconds
                    mins = int(start_time // 60)
                    secs = int(start_time % 60)
                    
                    # If speaker changes, flush the current block
                    if speaker != current_speaker and current_speaker is not None:
                        lines.append(f"**{current_speaker}** ({speaker_block[0]['time']} - {speaker_block[-1]['time']})")
                        # Add each sentence on its own line with timestamp
                        for block in speaker_block:
                            lines.append(f"[{block['time']}] {block['text']}")
                        lines.append("")
                        speaker_block = []
                    
                    current_speaker = speaker
                    speaker_block.append({
                        'time': f"{mins:02d}:{secs:02d}",
                        'text': text
                    })
            
            # Flush the last speaker block
            if speaker_block:
                lines.append(f"**{current_speaker}** ({speaker_block[0]['time']} - {speaker_block[-1]['time']})")
                # Add each sentence on its own line with timestamp
                for block in speaker_block:
                    lines.append(f"[{block['time']}] {block['text']}")
                lines.append("")
            
            content = '\n'.join(lines)
            if self._atomic_write(content, transcript_md_file):
                output_files.append(str(transcript_md_file))
                logger.info(f"  ✅ {transcript_md_file.name}")
        
        
        # Clear temp files list since all were successful
        if self.current_task:
            self.current_task['temp_files'] = []
        
        return output_files
    
    def save_overview_files(self, summary: Dict[str, Any], audio_path: Path, transcript_title: str = None, force: bool = False) -> list:
        """Save overview files separately when available"""
        logger.info("  📊 Overview available, saving overview files...")
        
        output_files = []
        
        # Determine output directory and base name
        if self.output_dir:
            output_base_dir = self.output_dir
            output_base_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_base_dir = audio_path.parent
        
        base_name = audio_path.name
        
        # Helper to check if file exists and handle force flag
        def should_write(file_path: Path) -> bool:
            if not file_path.exists():
                return True
            if force:
                logger.info(f"  ⚠️  Overwriting existing file: {file_path.name}")
                return True
            logger.warning(f"  ⏭️  Skipping existing file: {file_path.name} (use --force to overwrite)")
            return False
        
        # Only create overview files if summary actually exists and has content
        if summary and summary.get('overview'):
            # 1. Save overview JSON
            overview_json_file = output_base_dir / f"{base_name}.overview.json"
            if should_write(overview_json_file):
                content = json.dumps(summary, indent=2)
                if self._atomic_write(content, overview_json_file):
                    output_files.append(str(overview_json_file))
                    logger.info(f"  ✅ {overview_json_file.name}")
            
            # 2. Save overview as plain text (Fireflies style)
            overview_txt_file = output_base_dir / f"{base_name}.overview.txt"
            if should_write(overview_txt_file):
                lines = []
                
                # Title and date
                lines.append(transcript_title or audio_path.stem)
                lines.append("")
                lines.append(datetime.now().strftime('%B %d, %Y, %I:%M %p PDT'))
                lines.append("")
                
                # Keywords section
                if summary.get('keywords'):
                    lines.append("KEYWORDS")
                    lines.append("--------")
                    keywords = summary.get('keywords', [])
                    if keywords:
                        lines.append(", ".join(keywords))
                    lines.append("")
                
                # Overview section
                if summary.get('overview'):
                    lines.append("OVERVIEW")
                    lines.append("--------")
                    # Split overview into bullet points if it's a paragraph
                    overview_text = summary.get('overview', '')
                    if '\n' in overview_text:
                        for line in overview_text.split('\n'):
                            if line.strip():
                                # Check if line already starts with dash
                                if line.strip().startswith('-'):
                                    lines.append(line.strip())
                                else:
                                    lines.append(f"- {line.strip()}")
                    elif '. ' in overview_text:
                        for sentence in overview_text.split('. '):
                            if sentence.strip():
                                lines.append(f"- {sentence.strip()}{'.' if not sentence.strip().endswith('.') else ''}")
                    else:
                        if overview_text.strip().startswith('-'):
                            lines.append(overview_text.strip())
                        else:
                            lines.append(f"- {overview_text}")
                    lines.append("")
                
                # Key Points / Notes
                if summary.get('bullet_gist'):
                    lines.append("KEY POINTS")
                    lines.append("----------")
                    for line in summary.get('bullet_gist', '').split('\n'):
                        if line.strip():
                            # Check if line already starts with dash
                            if line.strip().startswith('-'):
                                lines.append(line.strip())
                            else:
                                lines.append(f"- {line.strip()}")
                    lines.append("")
                
                # Action Items
                if summary.get('action_items'):
                    lines.append("ACTION ITEMS")
                    lines.append("-----------")
                    for line in summary.get('action_items', '').split('\n'):
                        if line.strip():
                            # Check if line already starts with dash
                            if line.strip().startswith('-'):
                                lines.append(line.strip())
                            else:
                                lines.append(f"- {line.strip()}")
                    lines.append("")
                
                # Additional Notes
                if summary.get('shorthand_bullet'):
                    lines.append("ADDITIONAL NOTES")
                    lines.append("----------------")
                    lines.append(summary.get('shorthand_bullet', ''))
                    lines.append("")
                
                # Outline
                if summary.get('outline'):
                    lines.append("OUTLINE")
                    lines.append("-------")
                    outline_text = summary.get('outline', '')
                    if isinstance(outline_text, str):
                        lines.append(outline_text)
                    else:
                        lines.append(str(outline_text))
                    lines.append("")
                
                content = '\n'.join(lines)
                if self._atomic_write(content, overview_txt_file):
                    output_files.append(str(overview_txt_file))
                    logger.info(f"  ✅ {overview_txt_file.name}")
            
            # 3. Save overview as Markdown (Fireflies style)
            overview_md_file = output_base_dir / f"{base_name}.overview.md"
            if should_write(overview_md_file):
                lines = []
                lines.append(f"# {transcript_title or audio_path.stem}")
                lines.append("")
                lines.append(datetime.now().strftime('%B %d, %Y, %I:%M %p PDT'))
                lines.append("")
                
                # Keywords section
                if summary.get('keywords'):
                    lines.append("## Keywords")
                    keywords = summary.get('keywords', [])
                    if keywords:
                        lines.append(", ".join([f"`{k}`" for k in keywords]))
                    lines.append("")
                
                # Overview section
                if summary.get('overview'):
                    lines.append("## Overview")
                    lines.append("")
                    # Format overview as bullet points
                    overview_text = summary.get('overview', '')
                    if '\n' in overview_text:
                        # Handle multi-line overview (already has bullets)
                        for line in overview_text.split('\n'):
                            if line.strip():
                                # Check if line already starts with dash
                                if line.strip().startswith('-'):
                                    lines.append(line.strip())
                                else:
                                    lines.append(f"- {line.strip()}")
                    elif '. ' in overview_text:
                        # Handle sentence-based overview
                        for sentence in overview_text.split('. '):
                            if sentence.strip():
                                lines.append(f"- {sentence.strip()}{'.' if not sentence.strip().endswith('.') else ''}")
                    else:
                        # Single line overview
                        if overview_text.strip().startswith('-'):
                            lines.append(overview_text.strip())
                        else:
                            lines.append(f"- {overview_text}")
                    lines.append("")
                
                # Notes/Key Points section
                if summary.get('bullet_gist'):
                    lines.append("## Notes")
                    lines.append("")
                    # Format as detailed bullet points
                    for point in summary.get('bullet_gist', '').split('\n'):
                        if point.strip():
                            if point.strip().startswith('-'):
                                lines.append(point.strip())
                            else:
                                lines.append(f"- {point.strip()}")
                    lines.append("")
                
                # Action Items section
                if summary.get('action_items'):
                    lines.append("## Action items")
                    lines.append("")
                    lines.append("##### **Unassigned**")
                    for item in summary.get('action_items', '').split('\n'):
                        if item.strip():
                            if item.strip().startswith('-'):
                                lines.append(item.strip())
                            else:
                                lines.append(f"- {item.strip()}")
                    lines.append("")
                
                # Additional notes if available
                if summary.get('shorthand_bullet'):
                    lines.append("## Additional Notes")
                    lines.append("")
                    lines.append(summary.get('shorthand_bullet', ''))
                    lines.append("")
                
                # Outline if available
                if summary.get('outline'):
                    lines.append("## Outline")
                    lines.append("")
                    outline_text = summary.get('outline', '')
                    # Check if it's structured or plain text
                    if isinstance(outline_text, str):
                        lines.append(outline_text)
                    else:
                        lines.append(str(outline_text))
                    lines.append("")
                
                content = '\n'.join(lines)
                if self._atomic_write(content, overview_md_file):
                    output_files.append(str(overview_md_file))
                    logger.info(f"  ✅ {overview_md_file.name}")
        else:
            logger.info("  ⚠️  No overview content available")
        
        return output_files
    
    def process_audio_file(self, audio_path: Path, 
                          dry_run: bool = False, force: bool = False,
                          max_wait: int = 30, wait_for_overview: bool = True,
                          delete_skip: bool = False, delete_wait: bool = False,
                          delete_wait_interval: int = 30,
                          min_duration: float = 120.0, force_short: bool = False) -> ProcessingResult:
        """Main processing workflow"""
        start_time = datetime.now()
        
        # Generate unique hash for both reference and title
        unique_hash = uuid.uuid4().hex[:6]  # 6 char hash
        reference_id = f"{audio_path.stem}_{unique_hash}"
        
        # Add CLI tag to identify transcripts uploaded by this tool
        # This allows safe deletion without affecting other transcripts
        title = f"FIREFLIESCLI__{reference_id}"  # e.g., FIREFLIESCLI__test_multi_gpu_training_af50d4
        
        # Store current task for state saving
        self.current_task = {
            'audio_path': str(audio_path),
            'reference_id': reference_id,
            'title': title,
            'start_time': start_time.isoformat(),
            'temp_files': []
        }
        
        logger.info("=" * 70)
        logger.info(f"PROCESSING: {audio_path.name}")
        logger.info(f"Reference: {reference_id}")
        logger.info("=" * 70)
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No actual processing")
            return ProcessingResult(
                success=True,
                audio_file=str(audio_path),
                base_name=audio_path.name,
                error_message="Dry run - no processing performed"
            )
        
        # Check audio duration before uploading
        audio_duration = self.get_audio_duration(audio_path)
        if audio_duration and audio_duration < min_duration and not force_short:
            duration_mins = audio_duration / 60
            min_duration_mins = min_duration / 60
            logger.error(f"  ❌ Audio file too short: {duration_mins:.2f} minutes")
            logger.error(f"     Fireflies requires minimum {min_duration_mins:.1f} minutes")
            logger.error(f"     Use --force-short to override this check")
            logger.info("  💡 Alternatives for short files:")
            logger.info("     - Use OpenAI Whisper API or local Whisper")
            logger.info("     - Concatenate multiple short files together")
            logger.info("     - Use a different transcription service")
            return ProcessingResult(
                success=False,
                audio_file=str(audio_path),
                base_name=audio_path.name,
                error_message=f"Audio too short ({duration_mins:.2f} min < {min_duration_mins:.1f} min minimum)"
            )
        elif audio_duration and audio_duration < min_duration and force_short:
            duration_mins = audio_duration / 60
            logger.warning(f"  ⚠️  Audio file is short ({duration_mins:.2f} min) but continuing with --force-short")
            logger.warning(f"     Transcript may return empty content")
        
        try:
            # Check if already processed (unless force flag is set)
            if not force:
                output_base_dir = self.output_dir if self.output_dir else audio_path.parent
                transcript_file = output_base_dir / f"{audio_path.name}.transcript.json"
                if transcript_file.exists():
                    logger.info("⏭️  Already processed, skipping... (use --force to reprocess)")
                    return ProcessingResult(
                        success=True,
                        audio_file=str(audio_path),
                        base_name=audio_path.name,
                        error_message="Already processed"
                    )
            
            # Step 1: Upload to tmpfiles.org
            audio_url = self.upload_to_tmpfiles(audio_path)
            if not audio_url:
                raise Exception("Failed to upload to temporary hosting")
            
            # Step 2: Submit to Fireflies
            if not self.submit_to_fireflies(audio_url, title, reference_id):
                raise Exception("Failed to submit to Fireflies")
            
            # Step 3: Wait for processing
            transcript_id = self.wait_for_transcript(title[:30], max_wait_minutes=max_wait)
            if not transcript_id:
                raise Exception("Transcript not ready after timeout")
            
            # Step 4: Download transcript (without waiting for overview initially)
            transcript = self.download_transcript(transcript_id, wait_for_overview=False)
            if not transcript:
                raise Exception("Failed to download transcript")
            
            # Step 5: Save transcript files immediately
            # Use try/finally to ensure deletion happens even on failure
            try:
                output_files = self.save_transcript_files(transcript, audio_path, force=force)
            except Exception as e:
                logger.error(f"  ❌ Failed to save transcript files: {e}")
                output_files = []
                # Continue to deletion even if saving failed
            
            # Step 6: Wait for and save overview if requested
            if wait_for_overview:
                # Try to get overview with retry logic
                overview_ready = False
                overview_wait_start = time.time()
                max_overview_wait = 300  # 5 minutes max for overview
                
                while not overview_ready and (time.time() - overview_wait_start) < max_overview_wait:
                    # Check if overview is ready
                    updated_transcript = self.download_transcript(transcript_id, wait_for_overview=False, checking_overview=True)
                    if updated_transcript and updated_transcript.get('summary') and updated_transcript['summary'].get('overview'):
                        overview_ready = True
                        logger.info(f"  ✅ Overview ready after {int(time.time() - overview_wait_start)}s wait!")
                        overview_files = self.save_overview_files(
                            updated_transcript['summary'], 
                            audio_path, 
                            transcript_title=updated_transcript.get('title'),
                            force=force
                        )
                        output_files.extend(overview_files)
                        # Update transcript with the overview for metrics
                        transcript = updated_transcript
                    else:
                        elapsed = int(time.time() - overview_wait_start)
                        if elapsed % 30 == 0 and elapsed > 0:  # Log every 30s
                            logger.info(f"  ⏳ Still waiting for overview... ({elapsed}s elapsed)")
                        time.sleep(10)  # Check every 10 seconds
                
                if not overview_ready:
                    logger.warning("  ⚠️  Overview not available after 5 minutes (may still be processing)")
            
            # Step 7: Delete from Fireflies (unless --delete-skip flag is set)
            # This happens even if saving failed, to avoid orphaned transcripts
            if not delete_skip:
                try:
                    self.delete_transcript(transcript_id, wait_for_deletion=delete_wait, check_interval=delete_wait_interval)
                except Exception as e:
                    logger.error(f"  ❌ Failed to delete transcript: {e}")
                    logger.error(f"     Manual deletion required for ID: {transcript_id}")
            else:
                logger.info("  ℹ️  Skipping deletion (--delete-skip flag set)")
            
            # Calculate metrics
            duration = int((datetime.now() - start_time).total_seconds())
            sentences = transcript.get('sentences') or []  # Handle null sentences
            word_count = sum(len(s.get('text', '').split()) for s in sentences) if sentences else 0
            has_summary = bool(transcript.get('summary') and 
                             transcript['summary'].get('overview'))
            
            logger.info(f"✅ SUCCESS! Processed in {duration}s")
            
            return ProcessingResult(
                success=True,
                audio_file=str(audio_path),
                base_name=audio_path.name,
                transcript_id=transcript_id,
                word_count=word_count,
                duration_seconds=0,  # API returns unreliable duration
                has_summary=has_summary,
                processing_time_seconds=duration,
                output_files=output_files
            )
            
        except Exception as e:
            duration = int((datetime.now() - start_time).total_seconds())
            logger.error(f"❌ FAILED after {duration}s: {e}")
            
            return ProcessingResult(
                success=False,
                audio_file=str(audio_path),
                base_name=audio_path.name,
                error_message=str(e),
                processing_time_seconds=duration
            )
        
        finally:
            self.current_task = None


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Fireflies Transcription CLI - Upload audio and get transcript/summary',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single audio file
  %(prog)s audio.opus
  
  # Use custom output directory
  %(prog)s audio.opus --output-dir transcripts/
  
  # Force reprocessing even if output exists
  %(prog)s audio.opus --force
  
  # Dry run to test without processing
  %(prog)s audio.opus --dry-run
  
  # Debug mode with verbose logging
  %(prog)s audio.opus --debug
  
  # Custom wait timeout for long files
  %(prog)s large_audio.opus --max-wait 60

Output Files:
  Creates 6 files alongside the input (or in --output-dir):
  - audio.opus.transcript.json  (full data)
  - audio.opus.transcript.txt   (plain text)
  - audio.opus.transcript.md    (markdown with timestamps)
  - audio.opus.summary.json     (summary data if available)
  - audio.opus.summary.txt      (plain text summary)
  - audio.opus.summary.md       (formatted summary)

Environment Variables:
  FIREFLIES_API_KEY    Fireflies API key (required)
        """
    )
    
    # Required arguments
    parser.add_argument('audio_file', 
                       help='Path to audio file (OPUS, MP3, WAV, M4A, etc.)')
    
    # Optional arguments
    parser.add_argument('--output-dir',
                       help='Output directory (default: same as input file)')
    parser.add_argument('--log-dir',
                       help='Directory for log files (default: no file logging)')
    parser.add_argument('--max-wait', type=int, default=30,
                       help='Max minutes to wait for transcript (default: 30)')
    
    # Flags
    parser.add_argument('--dry-run', action='store_true',
                       help='Test run without actual processing')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    parser.add_argument('--force', action='store_true',
                       help='Force reprocessing even if output exists')
    parser.add_argument('--overview-skip', action='store_true',
                       help="Skip waiting for AI overview (faster but may miss overview)")
    parser.add_argument('--delete-skip', action='store_true',
                       help='Skip deletion from Fireflies (default: delete after download)')
    parser.add_argument('--delete-wait', action='store_true',
                       help='Wait for deletion to complete (adds 5-15 min, for testing)')
    parser.add_argument('--delete-wait-interval', type=int, default=30,
                       help='Seconds between deletion checks when using --delete-wait (default: 30)')
    parser.add_argument('--min-duration', type=float, default=120.0,
                       help='Minimum audio duration in seconds (default: 120s/2min, Fireflies limitation)')
    parser.add_argument('--force-short', action='store_true',
                       help='Process files shorter than min-duration anyway (may return empty transcript)')
    
    args = parser.parse_args()
    
    # Setup logging with file support
    global logger
    log_dir = Path(args.log_dir) if args.log_dir else None
    logger = setup_logging(debug=args.debug, log_dir=log_dir)
    
    # Check API key
    api_key = os.environ.get('FIREFLIES_API_KEY')
    if not api_key:
        logger.error("❌ FIREFLIES_API_KEY environment variable not set")
        logger.error("Set it with: export FIREFLIES_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Validate audio file
    audio_path = Path(args.audio_file).resolve()
    if not audio_path.exists():
        logger.error(f"❌ Audio file not found: {audio_path}")
        sys.exit(1)
    
    # Create output directory if specified
    output_dir = None
    if args.output_dir:
        output_dir = Path(args.output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize transcriber
    transcriber = FirefliesTranscriber(
        api_key=api_key,
        output_dir=output_dir,
        debug=args.debug
    )
    
    # Process the file
    result = transcriber.process_audio_file(
        audio_path=audio_path,
        dry_run=args.dry_run,
        force=args.force,
        max_wait=args.max_wait,
        wait_for_overview=not args.overview_skip,
        delete_skip=args.delete_skip,
        delete_wait=args.delete_wait,
        delete_wait_interval=args.delete_wait_interval,
        min_duration=args.min_duration,
        force_short=args.force_short
    )
    
    # Print summary
    print("\n" + "=" * 70)
    print("PROCESSING SUMMARY")
    print("=" * 70)
    print(f"Success: {result.success}")
    print(f"Audio File: {result.audio_file}")
    
    if result.success and result.transcript_id:
        print(f"Transcript ID: {result.transcript_id}")
        print(f"Word Count: {result.word_count}")
        # Duration field is unreliable from API, don't display it
        print(f"Has Summary: {result.has_summary}")
        print(f"Processing Time: {result.processing_time_seconds}s")
        if result.output_files:
            print(f"\nOutput Files:")
            cwd = Path.cwd()
            for f in result.output_files:
                file_path = Path(f)
                try:
                    # Try to make path relative to current directory
                    relative_path = file_path.relative_to(cwd)
                    print(f"  - {relative_path}")
                except ValueError:
                    # Path is outside current directory, use absolute
                    print(f"  - {f}")
    elif result.error_message:
        print(f"Error: {result.error_message}")
    
    # Exit with appropriate code
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()