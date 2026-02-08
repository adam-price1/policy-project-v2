#!/usr/bin/env python3
"""
Insurance Policy PDF Crawler (Improved)

Phase 1: Discover policy PDFs from insurer websites

Improvements:
- ✅ Query string handling in PDF detection
- ✅ Domain normalization (www.example.com == example.com)
- ✅ URL normalization (removes tracking params)
- ✅ Better error handling (specific exception types)
- ✅ Seed file validation
- ✅ Statistics tracking
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
import os
import time
import logging

# =========================
# LOGGING SETUP
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("crawler")

# =========================
# CONFIG
# =========================

SEED_FILE = "seed_insurers.txt"
URL_OUTPUT_FILE = "urls.txt"
SEEN_PAGES_FILE = "seen_pages.txt"
SEEN_PDFS_FILE = "seen_pdfs.txt"

MAX_PAGES_PER_DOMAIN = 1000
REQUEST_DELAY = 0.5
TIMEOUT = 10

HEADERS = {
    "User-Agent": "PolicyCheckBot/1.0 (+https://policycheck.co.nz)"
}

# Tracking params to remove for deduplication
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "gclid", "fbclid", "v", "version", "ref", "download", "format"
}

# =========================
# PATH CONTROL
# =========================

ALLOWED_PATH_KEYWORDS = [
    "/insurance",
    "/policy",
    "/policies",
    "/documents",
    "/pds",
    "/product-disclosure"
]

DENY_PATH_KEYWORDS = [
    "/drivers/",
    "/membership/",
    "/travel/",
    "/home-services/",
    "/about/",
    "/careers/",
    "/site-info/",
    "/news/",
    "/media/",
    "/blog/",
    "/events/",
    "/rewards/",
    "/partners/"
]

# =========================
# HELPERS
# =========================

def load_lines(path):
    """Load set of strings from file."""
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def append_line(path, line):
    """Append line to file."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def is_pdf(url):
    """Check if URL points to a PDF (ignoring query strings)."""
    path = url.lower().split('?')[0].split('#')[0]
    return path.endswith(".pdf")

def normalize_domain(domain):
    """Normalize domain for comparison."""
    return domain.lower().lstrip("www.")

def same_domain(seed, url):
    """Check if URLs are on same domain (normalized)."""
    seed_domain = normalize_domain(urlparse(seed).netloc)
    url_domain = normalize_domain(urlparse(url).netloc)
    return seed_domain == url_domain

def normalize_url(url):
    """Remove tracking params to prevent duplicate downloads."""
    parsed = urlparse(url)
    
    if parsed.query:
        # Keep non-tracking params
        params = parse_qs(parsed.query, keep_blank_values=True)
        params = {k: v for k, v in params.items() 
                  if k.lower() not in TRACKING_PARAMS}
        
        # Sort for consistency
        query = urlencode(params, doseq=True) if params else ""
    else:
        query = ""
    
    # Reconstruct URL without fragment
    return urlunparse((
        parsed.scheme, parsed.netloc, parsed.path,
        parsed.params, query, ""
    ))

def is_allowed_path(url):
    """Check if path looks like policy section."""
    u = url.lower()

    # Block obvious non-insurance areas
    if any(d in u for d in DENY_PATH_KEYWORDS):
        return False

    # Must contain insurance-related keywords
    return any(k in u for k in ALLOWED_PATH_KEYWORDS)

def load_seeds():
    """Load and validate seed insurers."""
    if not os.path.exists(SEED_FILE):
        logger.error(f"Seed file not found: {SEED_FILE}")
        logger.info("Please create it with one insurer URL per line")
        return None
    
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        seeds = [line.strip() for line in f 
                 if line.strip() and not line.startswith("#")]
    
    if not seeds:
        logger.error(f"Seed file is empty or contains only comments")
        return None
    
    logger.info(f"Loaded {len(seeds)} seed URLs")
    return seeds

# =========================
# STATS
# =========================

class CrawlStats:
    def __init__(self):
        self.total_pages = 0
        self.total_pdfs = 0
        self.errors = 0
        self.errors_by_type = {}
    
    def add_error(self, error_type):
        self.errors += 1
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
    
    def print_summary(self):
        logger.info("=" * 60)
        logger.info("CRAWL SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total pages crawled: {self.total_pages}")
        logger.info(f"PDFs discovered:    {self.total_pdfs}")
        logger.info(f"Errors:             {self.errors}")
        
        if self.errors_by_type:
            logger.info("Error breakdown:")
            for error_type, count in sorted(
                self.errors_by_type.items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                logger.info(f"  {error_type}: {count}")
        
        logger.info("=" * 60)

# =========================
# MAIN CRAWLER
# =========================

def crawl():
    seeds = load_seeds()
    if not seeds:
        return
    
    seen_pages = load_lines(SEEN_PAGES_FILE)
    seen_pdfs = load_lines(SEEN_PDFS_FILE)
    stats = CrawlStats()

    logger.info(f"Starting crawl of {len(seeds)} insurer(s)")
    logger.info(f"Seen pages: {len(seen_pages)}")
    logger.info(f"Seen PDFs: {len(seen_pdfs)}")

    for seed in seeds:
        domain = urlparse(seed).netloc
        pages_crawled = 0
        queue = [seed]

        logger.info(f"\n🔍 Crawling domain: {domain}")

        while queue and pages_crawled < MAX_PAGES_PER_DOMAIN:
            url = queue.pop(0)

            if url in seen_pages:
                continue

            if not same_domain(seed, url):
                logger.debug(f"Skipping different domain: {url}")
                continue

            seen_pages.add(url)
            append_line(SEEN_PAGES_FILE, url)

            pages_crawled += 1
            stats.total_pages += 1
            logger.info(f"  Page {pages_crawled}: {url}")

            try:
                r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                
                if r.status_code != 200:
                    logger.warning(f"    HTTP {r.status_code}")
                    stats.add_error(f"HTTP {r.status_code}")
                    continue

                soup = BeautifulSoup(r.text, "html.parser")

                for link in soup.find_all("a", href=True):
                    href = link["href"].strip()
                    full_url = urljoin(url, href)

                    # PDF handling
                    if is_pdf(full_url):
                        # Normalize to prevent duplicates
                        normalized = normalize_url(full_url)
                        
                        if normalized not in seen_pdfs:
                            seen_pdfs.add(normalized)
                            append_line(SEEN_PDFS_FILE, normalized)
                            append_line(URL_OUTPUT_FILE, normalized)
                            logger.info(f"    📄 PDF found: {normalized}")
                            stats.total_pdfs += 1
                        continue

                    # Page crawl decision
                    if is_allowed_path(full_url) and full_url not in seen_pages:
                        queue.append(full_url)

                time.sleep(REQUEST_DELAY)

            except requests.exceptions.Timeout:
                logger.warning(f"    Timeout ({TIMEOUT}s)")
                stats.add_error("Timeout")
            
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"    Connection error: {e}")
                stats.add_error("Connection error")
            
            except requests.exceptions.HTTPError as e:
                logger.warning(f"    HTTP error: {e}")
                stats.add_error("HTTP error")
            
            except Exception as e:
                logger.warning(f"    Unexpected error: {e}")
                stats.add_error("Other error")

    stats.print_summary()

# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    crawl()
