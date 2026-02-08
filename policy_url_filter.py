#!/usr/bin/env python3
"""
Policy URL Filter (Improved)

Phase 1: Filter discovered URLs to real policy PDFs

Improvements:
- ✅ Query string handling in filename extraction
- ✅ Input/output validation
- ✅ Statistics tracking
- ✅ Better error messages
"""

import os
from urllib.parse import urlparse
import logging

# =========================
# LOGGING SETUP
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("filter")

# =========================
# CONFIG
# =========================

INPUT_FILE = "urls.txt"
OUTPUT_FILE = "policy_urls.txt"
FILTERED_FILE = "filtered_out_urls.txt"

KEEP_KEYWORDS = [
    "policy",
    "pds",
    "product-disclosure",
    "tmd",
    "policy-wording",
    "policy-document",
    "schedule",
    "insurance"
]

DROP_KEYWORDS = [
    "form",
    "application",
    "claim",
    "guide",
    "fsg",
    "brochure",
    "fact-sheet",
    "statement",
    "authority",
    "privacy",
    "terms",
    "cookies",
    "media",
    "news",
    "blog"
]

# =========================
# HELPERS
# =========================

def extract_filename(url):
    """Extract filename from URL (ignore query strings)."""
    parsed = urlparse(url)
    path = parsed.path
    filename = path.split("/")[-1].lower() if path else ""
    return filename

def should_keep(url):
    """Determine if URL looks like a real policy PDF."""
    filename = extract_filename(url)
    
    # Check extension
    if not filename.endswith(".pdf"):
        return False
    
    # Check blacklist (hard reject)
    if any(d in filename for d in DROP_KEYWORDS):
        return False
    
    # Check whitelist (must match)
    return any(k in filename for k in KEEP_KEYWORDS)

# =========================
# STATS
# =========================

class FilterStats:
    def __init__(self):
        self.total = 0
        self.kept = 0
        self.dropped = 0
    
    def add(self, keep):
        self.total += 1
        if keep:
            self.kept += 1
        else:
            self.dropped += 1
    
    def print_summary(self):
        logger.info("=" * 60)
        logger.info("FILTER SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total URLs:    {self.total}")
        logger.info(f"Kept:          {self.kept} ({100*self.kept/self.total:.1f}%)")
        logger.info(f"Dropped:       {self.dropped} ({100*self.dropped/self.total:.1f}%)")
        logger.info("=" * 60)

# =========================
# MAIN
# =========================

def main():
    # Validate input file
    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file not found: {INPUT_FILE}")
        logger.info("Please run policy_url_crawler.py first")
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
        logger.info("Please run policy_url_crawler.py first")
        return False
    
    logger.info(f"Filtering {len(urls)} URLs...")
    
    # Clear output files (fresh start)
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("")
        with open(FILTERED_FILE, "w", encoding="utf-8") as f:
            f.write("")
    except Exception as e:
        logger.error(f"Failed to clear output files: {e}")
        return False
    
    stats = FilterStats()
    
    # Filter URLs
    for url in urls:
        keep = should_keep(url)
        stats.add(keep)
        
        try:
            if keep:
                with open(OUTPUT_FILE, "a", encoding="utf-8") as out:
                    out.write(url + "\n")
                logger.debug(f"Keep: {extract_filename(url)}")
            else:
                with open(FILTERED_FILE, "a", encoding="utf-8") as out:
                    out.write(url + "\n")
                logger.debug(f"Drop: {extract_filename(url)}")
        except Exception as e:
            logger.error(f"Failed to write output: {e}")
            return False
    
    stats.print_summary()
    
    if stats.kept > 0:
        logger.info(f"✅ Next step: python admin_pdf_ingestor_v2.py")
    
    return True

# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
