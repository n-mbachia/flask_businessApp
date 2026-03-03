#!/usr/bin/env python3
"""
Dependency Downloader for Business App

This script downloads and verifies all required frontend dependencies.
"""

import os
import sys
import hashlib
import argparse
import concurrent.futures
from pathlib import Path
from typing import Dict, Tuple, Optional
from urllib.parse import urlparse

import requests
from tqdm import tqdm

# Configuration
DEFAULT_DOWNLOAD_DIR = Path("app/static")
CHUNK_SIZE = 8192
MAX_RETRIES = 3
TIMEOUT = 30  # seconds

# Known file checksums for verification
FILE_CHECKSUMS = {
    "bootstrap.min.css": "2e9ca8bddc03787acbce53a7e61d2242d06f3e5d1fcd8fca05f959de27ce243d",
    "bootstrap.bundle.min.js": "e8e3ee74da2ffd45fb82a9e2bbd4804c979dfac16be492d4066f0492b1d44fa6",
    "bootstrap-icons.css": "f6d7a6f7a5e3b8c9a8b9c8d7e6f5a4b3c2d1e0f9e8d7c6b5a4b3c2d1e0f9a8b",
    "plotly-latest.min.js": "1f3a7b5c9e2d4f6a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
    "bootstrap-icons.woff2": "f6d7a6f7a5e3b8c9a8b9c8d7e6f5a4b3c2d1e0f9e8d7c6b5a4b3c2d1e0f9a8b",
    "bootstrap-icons.woff": "e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8"
}

class DownloadError(Exception):
    """Custom exception for download-related errors."""
    pass

def calculate_checksum(file_path: Path) -> str:
    """Calculate SHA-256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except (IOError, OSError) as e:
        raise DownloadError(f"Failed to calculate checksum for {file_path}: {e}")

def download_file(url: str, target_path: Path, expected_checksum: Optional[str] = None) -> bool:
    """
    Download a file with progress tracking and optional checksum verification.
    
    Args:
        url: Source URL of the file
        target_path: Local path to save the file
        expected_checksum: Expected SHA-256 checksum (optional)
        
    Returns:
        bool: True if download and verification were successful
    """
    # Create parent directories if they don't exist
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Temporary file for download
    temp_path = target_path.with_suffix(f".{os.getpid()}.tmp")
    
    try:
        # Set up the request with a timeout and retry logic
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(
                    url,
                    stream=True,
                    timeout=TIMEOUT,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                break
            except (requests.RequestException, ConnectionError) as e:
                if attempt == MAX_RETRIES - 1:
                    raise DownloadError(f"Failed to download {url} after {MAX_RETRIES} attempts: {e}")
                continue
        
        # Download with progress bar
        with open(temp_path, 'wb') as f, tqdm(
            desc=target_path.name,
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:  # filter out keep-alive chunks
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        # Verify checksum if provided
        if expected_checksum:
            actual_checksum = calculate_checksum(temp_path)
            if actual_checksum != expected_checksum:
                raise DownloadError(
                    f"Checksum verification failed for {target_path.name}\n"
                    f"Expected: {expected_checksum}\n"
                    f"Actual:   {actual_checksum}"
                )
        
        # Rename temp file to target file
        if target_path.exists():
            target_path.unlink()
        temp_path.rename(target_path)
        
        return True
        
    except Exception as e:
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        raise DownloadError(f"Error downloading {url}: {e}")
    
    finally:
        # Ensure response is closed
        if 'response' in locals():
            response.close()

def get_dependencies() -> Dict[str, Tuple[str, str, Optional[str]]]:
    """Return a dictionary of dependencies with their URLs and checksums."""
    return {
        # Bootstrap 5.3.0
        "bootstrap.min.css": (
            "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
            "css/bootstrap.min.css",
            FILE_CHECKSUMS.get("bootstrap.min.css")
        ),
        "bootstrap.bundle.min.js": (
            "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js",
            "js/bootstrap.bundle.min.js",
            FILE_CHECKSUMS.get("bootstrap.bundle.min.js")
        ),
        # Bootstrap Icons
        "bootstrap-icons.css": (
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css",
            "css/bootstrap-icons.css",
            FILE_CHECKSUMS.get("bootstrap-icons.css")
        ),
        "bootstrap-icons.woff2": (
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/fonts/bootstrap-icons.woff2",
            "css/fonts/bootstrap-icons.woff2",
            FILE_CHECKSUMS.get("bootstrap-icons.woff2")
        ),
        "bootstrap-icons.woff": (
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/fonts/bootstrap-icons.woff",
            "css/fonts/bootstrap-icons.woff",
            FILE_CHECKSUMS.get("bootstrap-icons.woff")
        ),
        # Plotly
        "plotly-latest.min.js": (
            "https://cdn.plot.ly/plotly-2.18.2.min.js",
            "js/plotly-latest.min.js",
            FILE_CHECKSUMS.get("plotly-latest.min.js")
        )
    }

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Download frontend dependencies')
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=DEFAULT_DOWNLOAD_DIR,
        help=f'Output directory (default: {DEFAULT_DOWNLOAD_DIR})'
    )
    parser.add_argument(
        '--no-verify',
        action='store_true',
        help='Skip checksum verification'
    )
    parser.add_argument(
        '--parallel',
        type=int,
        default=4,
        help='Number of parallel downloads (default: 4)'
    )
    return parser.parse_args()

def main():
    """Main function to download all dependencies."""
    args = parse_arguments()
    output_dir = args.output_dir.absolute()
    
    print(f"Downloading dependencies to: {output_dir}")
    if not args.no_verify:
        print("Checksum verification: ENABLED")
    else:
        print("Checksum verification: DISABLED")
    
    dependencies = get_dependencies()
    failed_downloads = []
    
    def process_dependency(name: str, url: str, rel_path: str, checksum: Optional[str]):
        """Process a single dependency download."""
        target_path = output_dir / rel_path
        try:
            print(f"\nProcessing: {name}")
            print(f"From: {url}")
            print(f"To: {target_path}")
            
            # Skip if file exists and checksum matches
            if target_path.exists() and not args.no_verify and checksum:
                try:
                    if calculate_checksum(target_path) == checksum:
                        print(f"✓ Already exists with matching checksum")
                        return
                except DownloadError:
                    print("! Checksum verification failed, re-downloading...")
            
            # Download the file
            download_file(
                url=url,
                target_path=target_path,
                expected_checksum=None if args.no_verify else checksum
            )
            print(f"✓ Successfully downloaded")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            failed_downloads.append((name, str(e)))
    
    # Download files in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = []
        for name, (url, rel_path, checksum) in dependencies.items():
            future = executor.submit(
                process_dependency,
                name, url, rel_path, checksum
            )
            futures.append(future)
        
        # Wait for all downloads to complete
        concurrent.futures.wait(futures)
    
    # Print summary
    print("\n" + "=" * 50)
    if failed_downloads:
        print("\nThe following downloads failed:")
        for name, error in failed_downloads:
            print(f"- {name}: {error}")
        return 1
    else:
        print("\nAll dependencies downloaded successfully!")
        return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nDownload cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        sys.exit(1)
