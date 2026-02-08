#!/usr/bin/env python3
"""
Admin PDF Ingestor (Improved)

Phase 1: Download and validate policy PDFs

Improvements:
- ✅ PDF validation (magic bytes, Content-Type, size)
- ✅ Better metadata tracking (HTTP status, errors, file size)
- ✅ Better error handling (specific exception types)
- ✅ Statistics tracking
- ✅ Safer filename generation
"""

import os
import json
import requests
import re
import logging
from datetime import datetime
from pathlib import Path

# =========================
# LOGGING SETUP
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ingestor")

# =========================
# CONFIG
# =========================

INPUT_FILE = "policy_urls.txt"
RAW_DIR = "raw_documents"
META_DIR = "metadata"

TIMEOUT = 30
MIN_PDF_SIZE_KB = 20
MAX_PDF_SIZE_MB = 100

# =========================
# HELPERS
# =========================

def safe_filename(url):
    """Generate a safe, unique filename from URL."""
    # Extract filename from path
    path = url.split("/")[-1] or "document.pdf"
    
    # Lowercase and remove special characters
    filename = path.lower()
    filename = re.sub(r"[^\w.\-]", "_", filename)
    
    # Ensure .pdf extension
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    
    # Limit length
    filename = filename[:200]
    
    return filename

def is_valid_pdf(response, filename):
    """Validate that response is a real PDF."""
    # Check Content-Type header
    ctype = response.headers.get("Content-Type", "").lower()
    if "pdf" not in ctype:
        return False, f"Content-Type not PDF: {ctype}"
    
    # Check magic bytes (PDF signature)
    if not response.content.startswith(b"%PDF"):
        return False, "Invalid PDF signature (not starting with %PDF)"
    
    # Check minimum size
    size_kb = len(response.content) / 1024
    if size_kb < MIN_PDF_SIZE_KB:
        return False, f"PDF too small ({size_kb:.1f}KB < {MIN_PDF_SIZE_KB}KB)"
    
    # Check maximum size
    size_mb = len(response.content) / (1024 * 1024)
    if size_mb > MAX_PDF_SIZE_MB:
        return False, f"PDF too large ({size_mb:.1f}MB > {MAX_PDF_SIZE_MB}MB)"
    
    return True, "Valid"

# =========================
# METADATA
# =========================

def create_metadata(url, filename, response=None, error=None):
    """Create metadata record for a download."""
    size_kb = None
    
    if response and response.content:
        size_kb = round(len(response.content) / 1024, 2)
    
    metadata = {
        "file_name": filename,
        "source_url": url,
        "download_date": datetime.utcnow().isoformat(),
        "http_status": response.status_code if response else None,
        "file_size_kb": size_kb,
        "success": error is None,
        "error": error,
        # Phase 2 fields (placeholders for future classification)
        "country": "Unknown",
        "insurer": "Unknown",
        "insurance_line": "Unknown",
        "product_name": "Unknown",
        "status": "needs_classification"
    }
    
    return metadata

# =========================
# DOWNLOADER
# =========================

def download_and_save(url, pdf_path, meta_path):
    """Download PDF and save with metadata."""
    metadata = None
    
    try:
        # Check if already downloaded
        if os.path.exists(pdf_path):
            metadata = create_metadata(url, os.path.basename(pdf_path))
            metadata["success"] = True
            metadata["skipped"] = True
            return metadata, "skipped"
        
        # Fetch URL
        logger.info(f"Downloading: {os.path.basename(pdf_path)}")
        
        r = requests.get(url, timeout=TIMEOUT)
        
        if r.status_code != 200:
            error = f"HTTP {r.status_code}"
            metadata = create_metadata(url, os.path.basename(pdf_path), r, error)
            logger.warning(f"  ⚠️ {error}")
            return metadata, "failed"
        
        # Validate PDF
        is_valid, reason = is_valid_pdf(r, os.path.basename(pdf_path))
        if not is_valid:
            metadata = create_metadata(url, os.path.basename(pdf_path), r, reason)
            logger.warning(f"  ⚠️ {reason}")
            return metadata, "failed"
        
        # Save PDF
        with open(pdf_path, "wb") as f:
            f.write(r.content)
        
        metadata = create_metadata(url, os.path.basename(pdf_path), r)
        logger.info(f"  ✅ Downloaded ({metadata['file_size_kb']}KB)")
        return metadata, "downloaded"
    
    except requests.exceptions.Timeout:
        error = f"Timeout ({TIMEOUT}s)"
        metadata = create_metadata(url, os.path.basename(pdf_path), error=error)
        logger.warning(f"  ⚠️ {error}")
        return metadata, "failed"
    
    except requests.exceptions.ConnectionError as e:
        error = "Connection error"
        metadata = create_metadata(url, os.path.basename(pdf_path), error=error)
        logger.warning(f"  ⚠️ {error}: {e}")
        return metadata, "failed"
    
    except requests.exceptions.RequestException as e:
        error = f"Request error: {str(e)[:80]}"
        metadata = create_metadata(url, os.path.basename(pdf_path), error=error)
        logger.warning(f"  ⚠️ {error}")
        return metadata, "failed"
    
    except Exception as e:
        error = str(e)[:120]
        metadata = create_metadata(url, os.path.basename(pdf_path), error=error)
        logger.error(f"  ⚠️ Unexpected error: {error}")
        return metadata, "failed"
    
    finally:
        # Always save metadata
        if metadata:
            try:
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to write metadata: {e}")

# =========================
# STATS
# =========================

class IngestStats:
    def __init__(self):
        self.total = 0
        self.downloaded = 0
        self.skipped = 0
        self.failed = 0
        self.errors = {}
    
    def add(self, status, error=None):
        self.total += 1
        
        if status == "downloaded":
            self.downloaded += 1
        elif status == "skipped":
            self.skipped += 1
        elif status == "failed":
            self.failed += 1
            if error:
                self.errors[error] = self.errors.get(error, 0) + 1
    
    def print_summary(self):
        logger.info("=" * 60)
        logger.info("INGESTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total URLs:        {self.total}")
        logger.info(f"Downloaded:        {self.downloaded}")
        logger.info(f"Skipped (exist):   {self.skipped}")
        logger.info(f"Failed:            {self.failed}")
        
        if self.errors:
            logger.info("Failed breakdown:")
            for error, count in sorted(
                self.errors.items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                logger.info(f"  {error}: {count}")
        
        logger.info("=" * 60)

# =========================
# MAIN
# =========================

def main():
    # Create directories
    Path(RAW_DIR).mkdir(exist_ok=True)
    Path(META_DIR).mkdir(exist_ok=True)
    
    # Validate input file
    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file not found: {INPUT_FILE}")
        logger.info("Please run policy_url_filter.py first")
        return False
    
    # Load URLs
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            urls = [l.strip() for l in f if l.strip()]
    except Exception as e:
        logger.error(f"Failed to read {INPUT_FILE}: {e}")
        return False
    
    if not urls:
        logger.error(f"{INPUT_FILE} is empty")
        logger.info("Please run policy_url_filter.py first")
        return False
    
    logger.info("=" * 60)
    logger.info("POLICY PDF INGESTION")
    logger.info("=" * 60)
    logger.info(f"Starting ingestion of {len(urls)} URLs")
    logger.info("")
    
    stats = IngestStats()
    
    # Download each PDF
    for url in urls:
        filename = safe_filename(url)
        pdf_path = os.path.join(RAW_DIR, filename)
        meta_path = os.path.join(META_DIR, filename + ".json")
        
        metadata, status = download_and_save(url, pdf_path, meta_path)
        
        if metadata:
            error = metadata.get("error")
            stats.add(status, error)
    
    stats.print_summary()
    
    if stats.failed > 0:
        logger.info(f"💡 Some downloads failed. Check logs above for details.")
    
    if stats.downloaded > 0:
        logger.info(f"✅ Successfully downloaded {stats.downloaded} PDFs")
    
    return True

# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
