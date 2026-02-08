# CODE IMPROVEMENT SUGGESTIONS - Phase 1 Pipeline

**Policy Check Insurance PDF Ingestion**  
**Date:** 2026-02-08  
**Scope:** Enhancements for current code (not Phase 2 features)

---

## Executive Summary

The current code is **clean and functional** for Phase 1. Below are suggestions to make it more robust, maintainable, and production-ready. All suggestions are **optional** and maintain the Phase 1 scope.

**Priority:**
- 🔴 **Critical:** Will cause failures or data loss
- 🟠 **High:** Improves reliability significantly
- 🟡 **Medium:** Better UX, easier debugging
- 🟢 **Low:** Code quality, nice-to-have

---

## 1. `policy_url_crawler.py` Improvements

### 1.1 🔴 CRITICAL: Query String Handling in PDF Detection

**Current Code (Line 68):**
```python
def is_pdf(url):
    return url.lower().endswith(".pdf")
```

**Problem:**
- `https://example.com/policy.pdf?v=1` returns `False` (wrong!)
- Query strings are legitimate; PDFs can have params

**Suggested Fix:**
```python
def is_pdf(url):
    """Check if URL points to a PDF (ignoring query strings)."""
    path = url.lower().split('?')[0]  # Remove query string
    return path.endswith(".pdf")
```

**Test:**
```python
assert is_pdf("https://example.com/policy.pdf?v=1")
assert is_pdf("https://example.com/policy.pdf#page=1")
```

---

### 1.2 🔴 CRITICAL: Domain Normalization

**Current Code (Line 70-71):**
```python
def same_domain(seed, url):
    return urlparse(seed).netloc == urlparse(url).netloc
```

**Problem:**
- `www.example.com` ≠ `example.com` (treats as different domains)
- Crawler misses www variants of sites

**Suggested Fix:**
```python
def same_domain(seed, url):
    """Check if URLs are on the same domain (normalized)."""
    def normalize(domain):
        return domain.lower().lstrip("www.")
    
    seed_domain = normalize(urlparse(seed).netloc)
    url_domain = normalize(urlparse(url).netloc)
    return seed_domain == url_domain
```

**Test:**
```python
assert same_domain("https://example.com", "https://www.example.com")
assert same_domain("https://www.qbe.com/au", "https://qbe.com/au")
```

---

### 1.3 🟠 HIGH: URL Normalization (Deduplication)

**Current Code:**
PDFs like `policy.pdf?v=1` and `policy.pdf?v=2` stored as separate URLs.

**Problem:**
- Duplicate downloads (wastes bandwidth)
- Tracking parameters (`?utm_source=`, etc.) create false duplicates

**Suggested Fix:**
```python
from urllib.parse import urlparse, parse_qs, urlencode

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", 
    "utm_content", "utm_term", "gclid", "fbclid"
}

def normalize_url(url):
    """Remove tracking params to prevent duplicate downloads."""
    parsed = urlparse(url)
    
    if parsed.query:
        # Keep non-tracking params
        params = parse_qs(parsed.query, keep_blank_values=True)
        params = {k: v for k, v in params.items() 
                  if k.lower() not in TRACKING_PARAMS}
        query = urlencode(params, doseq=True) if params else ""
    else:
        query = ""
    
    # Reconstruct URL
    from urllib.parse import urlunparse
    return urlunparse((
        parsed.scheme, parsed.netloc, parsed.path,
        parsed.params, query, ""  # Remove fragment
    ))
```

**Usage:**
```python
# In main crawler loop:
if is_pdf(full_url):
    normalized = normalize_url(full_url)
    if normalized not in seen_pdfs:
        seen_pdfs.add(normalized)
        append_line(SEEN_PDFS_FILE, normalized)
        append_line(URL_OUTPUT_FILE, normalized)
```

---

### 1.4 🟠 HIGH: Better Error Handling

**Current Code (Line 147-148):**
```python
except requests.exceptions.RequestException as e:
    print(f"  ⚠️ Connection error: {e}")
    continue
```

**Suggestion:** Distinguish between error types

```python
except requests.exceptions.Timeout:
    print(f"  ⚠️ Timeout ({TIMEOUT}s)")
except requests.exceptions.ConnectionError:
    print(f"  ⚠️ Connection refused")
except requests.exceptions.HTTPError as e:
    print(f"  ⚠️ HTTP error: {e.response.status_code}")
except requests.exceptions.RequestException as e:
    print(f"  ⚠️ Request error: {e}")
```

---

### 1.5 🟡 MEDIUM: Content-Type Validation

**Current Code:**
PDFs are detected by `.pdf` extension only.

**Suggestion:** Check Content-Type header too

```python
def is_likely_pdf(response, url):
    """Check if response is actually a PDF."""
    # Check header
    ctype = response.headers.get("Content-Type", "").lower()
    if "pdf" in ctype:
        return True
    
    # Fallback to URL extension
    return url.lower().endswith(".pdf")

# In crawler:
r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
if r.status_code == 200 and is_likely_pdf(r, url):
    # Process...
```

---

### 1.6 🟡 MEDIUM: Logging & Statistics

**Suggestion:** Track statistics during crawl

```python
class CrawlStats:
    def __init__(self):
        self.total_pages = 0
        self.pdfs_found = 0
        self.errors = 0
    
    def print_summary(self):
        print(f"\n📊 Crawl Summary:")
        print(f"  Total pages crawled: {self.total_pages}")
        print(f"  PDFs discovered: {self.pdfs_found}")
        print(f"  Errors: {self.errors}")

# In crawl():
stats = CrawlStats()
# ... update stats in main loop
stats.print_summary()
```

---

### 1.7 🟡 MEDIUM: Seed File Validation

**Current Code (Line 88-90):**
```python
if not os.path.exists(SEED_FILE):
    print(f"❌ ERROR: Seed file not found: {SEED_FILE}")
    return
```

**Suggestion:** Check seed list is non-empty

```python
def load_seeds():
    """Load and validate seed insurers."""
    if not os.path.exists(SEED_FILE):
        print(f"❌ ERROR: {SEED_FILE} not found")
        print(f"   Please create it with one insurer URL per line")
        return None
    
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        seeds = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    if not seeds:
        print(f"❌ ERROR: {SEED_FILE} is empty or contains only comments")
        return None
    
    print(f"✅ Loaded {len(seeds)} seed URLs")
    return seeds

# In crawl():
seeds = load_seeds()
if not seeds:
    return
```

---

## 2. `policy_url_filter.py` Improvements

### 2.1 🔴 CRITICAL: Query String Handling

**Current Code (Line 27-31):**
```python
def should_keep(url):
    u = url.lower()
    if any(d in u for d in DROP_KEYWORDS):
        return False
    return any(k in u for k in KEEP_KEYWORDS)
```

**Problem:**
- `https://example.com/policy.pdf?v=1` is not matched by `"policy"` keyword
- Query strings can push filename beyond keyword check

**Suggested Fix:**
```python
def should_keep(url):
    """Determine if URL looks like a real policy PDF."""
    # Extract filename from URL (remove query/fragment)
    from urllib.parse import urlparse
    parsed = urlparse(url)
    filename = parsed.path.split("/")[-1].lower()
    
    # Check extension
    if not filename.endswith(".pdf"):
        return False
    
    # Check blacklist (hard reject)
    if any(d in filename for d in DROP_KEYWORDS):
        return False
    
    # Check whitelist (must match)
    return any(k in filename for k in KEEP_KEYWORDS)
```

---

### 2.2 🟠 HIGH: Input/Output Validation

**Current Code (Line 33-36):**
```python
if not os.path.exists(INPUT_FILE):
    print("❌ urls.txt not found")
    return
```

**Suggestion:** Check for empty input and validate output

```python
def main():
    # Validate input
    if not os.path.exists(INPUT_FILE):
        print(f"❌ {INPUT_FILE} not found")
        print("   Run policy_url_crawler.py first")
        return False
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        urls = [l.strip() for l in f if l.strip()]
    
    if not urls:
        print(f"❌ {INPUT_FILE} is empty")
        return False
    
    # Clear output files (fresh start)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("")
    with open(FILTERED_FILE, "w", encoding="utf-8") as f:
        f.write("")
    
    kept, dropped = 0, 0
    for url in urls:
        if should_keep(url):
            with open(OUTPUT_FILE, "a", encoding="utf-8") as out:
                out.write(url + "\n")
            kept += 1
        else:
            with open(FILTERED_FILE, "a", encoding="utf-8") as out:
                out.write(url + "\n")
            dropped += 1
    
    print(f"✅ Filter complete")
    print(f"   Kept:    {kept}")
    print(f"   Dropped: {dropped}")
    print(f"   Ratio:   {100*kept/(kept+dropped):.1f}% kept")
    
    return True
```

---

### 2.3 🟡 MEDIUM: Better Keyword Configuration

**Current Code:**
Keywords hardcoded in script.

**Suggestion:** Load from external file for easier tuning

```python
# filter_keywords.json
{
  "keep": [
    "policy", "pds", "product-disclosure", "tmd", 
    "policy-wording", "policy-document", "schedule"
  ],
  "drop": [
    "form", "application", "claim", "guide", "fsg",
    "brochure", "fact-sheet", "statement", "authority",
    "privacy", "terms", "cookies"
  ]
}
```

```python
import json

def load_keywords():
    """Load filtering keywords from JSON file."""
    with open("filter_keywords.json", "r") as f:
        config = json.load(f)
    return config["keep"], config["drop"]

KEEP_KEYWORDS, DROP_KEYWORDS = load_keywords()
```

---

## 3. `admin_pdf_ingestor_v2.py` Improvements

### 3.1 🔴 CRITICAL: PDF Validation

**Current Code (Line 34-40):**
```python
r = requests.get(url, timeout=30)
if r.status_code != 200:
    print("  ⚠️ Download failed")
    continue

with open(pdf_path, "wb") as f:
    f.write(r.content)
```

**Problems:**
- No check that response is actually a PDF
- No check for Content-Type header
- No minimum file size check
- Could download HTML error pages as "PDFs"

**Suggested Fix:**
```python
def is_valid_pdf(response, filename):
    """Validate that response is a real PDF."""
    # Check Content-Type
    ctype = response.headers.get("Content-Type", "").lower()
    if "pdf" not in ctype:
        return False, "Content-Type not PDF"
    
    # Check magic bytes (PDF signature)
    if not response.content.startswith(b"%PDF"):
        return False, "Invalid PDF signature"
    
    # Check minimum size (bytes)
    MIN_SIZE_KB = 20
    if len(response.content) < MIN_SIZE_KB * 1024:
        return False, f"PDF too small ({len(response.content)/1024:.1f}KB)"
    
    # Check maximum size (prevent huge downloads)
    MAX_SIZE_MB = 100
    if len(response.content) > MAX_SIZE_MB * 1024 * 1024:
        return False, f"PDF too large ({len(response.content)/(1024*1024):.1f}MB)"
    
    return True, "Valid"

# In main loop:
try:
    r = requests.get(url, timeout=30)
    if r.status_code != 200:
        raise ValueError(f"HTTP {r.status_code}")
    
    is_valid, reason = is_valid_pdf(r, filename)
    if not is_valid:
        raise ValueError(reason)
    
    with open(pdf_path, "wb") as f:
        f.write(r.content)
    
    metadata["success"] = True
    metadata["size_kb"] = round(len(r.content) / 1024, 2)
    
except Exception as e:
    metadata["error"] = str(e)
    print(f"  ⚠️ Failed: {str(e)}")
```

---

### 3.2 🟠 HIGH: Better Metadata Tracking

**Current Code (Line 42-50):**
```python
metadata = {
    "file_name": filename,
    "source_url": url,
    "download_date": datetime.utcnow().isoformat(),
    "country": "Unknown",
    "insurer": "Unknown",
    "insurance_line": "Unknown",
    "product_name": "Unknown",
    "status": "needs_classification"
}
```

**Suggestion:** Add HTTP status and error tracking

```python
def create_metadata(url, filename, response=None, error=None):
    """Create metadata record for a download."""
    metadata = {
        "file_name": filename,
        "source_url": url,
        "download_date": datetime.utcnow().isoformat(),
        "http_status": response.status_code if response else None,
        "file_size_kb": round(len(response.content) / 1024, 2) if response else None,
        "success": error is None,
        "error": error,
        # Phase 2 fields (placeholders)
        "country": "Unknown",
        "insurer": "Unknown",
        "insurance_line": "Unknown",
        "product_name": "Unknown",
        "status": "needs_classification"
    }
    return metadata
```

---

### 3.3 🟠 HIGH: Better Error Handling

**Current Code (Line 56-57):**
```python
except Exception as e:
    print("  ⚠️ Error:", e)
```

**Suggestion:** Track specific error types

```python
def download_and_save(url, pdf_path, meta_path):
    """Download PDF and save with metadata."""
    try:
        r = requests.get(url, timeout=30)
        
        if r.status_code != 200:
            return create_metadata(url, os.path.basename(pdf_path), 
                                   error=f"HTTP {r.status_code}")
        
        is_valid, reason = is_valid_pdf(r, os.path.basename(pdf_path))
        if not is_valid:
            return create_metadata(url, os.path.basename(pdf_path), 
                                   error=reason)
        
        # Save PDF
        with open(pdf_path, "wb") as f:
            f.write(r.content)
        
        metadata = create_metadata(url, os.path.basename(pdf_path), r)
        
    except requests.exceptions.Timeout:
        metadata = create_metadata(url, os.path.basename(pdf_path), 
                                   error="Timeout (30s)")
    except requests.exceptions.ConnectionError:
        metadata = create_metadata(url, os.path.basename(pdf_path), 
                                   error="Connection error")
    except Exception as e:
        metadata = create_metadata(url, os.path.basename(pdf_path), 
                                   error=str(e))
    
    # Save metadata
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    return metadata
```

---

### 3.4 🟡 MEDIUM: Statistics & Summary

**Current Code (Line 59):**
```python
print("✅ Ingestion complete")
```

**Suggestion:** Show statistics

```python
class IngestStats:
    def __init__(self):
        self.total = 0
        self.downloaded = 0
        self.skipped = 0
        self.failed = 0
        self.errors = {}
    
    def print_summary(self):
        print("\n" + "="*50)
        print("INGESTION SUMMARY")
        print("="*50)
        print(f"Total URLs:       {self.total}")
        print(f"Downloaded:       {self.downloaded}")
        print(f"Skipped (exist):  {self.skipped}")
        print(f"Failed:           {self.failed}")
        
        if self.errors:
            print("\nError breakdown:")
            for error, count in sorted(self.errors.items(), 
                                       key=lambda x: x[1], reverse=True):
                print(f"  {error}: {count}")
        
        print("="*50)
```

---

### 3.5 🟡 MEDIUM: Safer Filename Generation

**Current Code (Line 13-14):**
```python
def safe_filename(url):
    return url.split("/")[-1].replace("?", "_")
```

**Suggestion:** More robust filename handling

```python
import re

def safe_filename(url):
    """Generate a safe, unique filename from URL."""
    from urllib.parse import urlparse
    
    # Extract filename from path
    path = urlparse(url).path
    filename = path.split("/")[-1] or "document.pdf"
    
    # Lowercase and remove special characters
    filename = filename.lower()
    filename = re.sub(r"[^\w.\-]", "_", filename)
    
    # Ensure .pdf extension
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    
    # Limit length
    filename = filename[:200]
    
    return filename

# Test
assert safe_filename("https://example.com/My Policy (v2).pdf?v=1") == "my_policy_v2_.pdf"
```

---

### 3.6 🟢 LOW: Logging to File

**Suggestion:** Save logs for debugging

```python
import logging

def setup_logging():
    """Configure logging to file and console."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[
            logging.FileHandler("ingest.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("ingestor")

logger = setup_logging()

# In main:
logger.info(f"Starting ingestion of {len(urls)} URLs")
logger.info(f"Downloaded {filename}")
logger.warning(f"Failed: {url} - {error}")
```

---

## 4. General Improvements

### 4.1 🟡 MEDIUM: Configuration File

Create `config.json` instead of hardcoding values:

```json
{
  "crawler": {
    "seed_file": "seed_insurers.txt",
    "max_pages_per_domain": 1000,
    "request_delay": 0.5,
    "timeout": 10,
    "user_agent": "PolicyCheckBot/1.0"
  },
  "filter": {
    "keep_keywords": ["policy", "pds", "product-disclosure"],
    "drop_keywords": ["form", "claim", "guide"]
  },
  "ingestor": {
    "input_file": "policy_urls.txt",
    "raw_dir": "raw_documents",
    "meta_dir": "metadata",
    "timeout": 30,
    "min_size_kb": 20,
    "max_size_mb": 100
  }
}
```

---

### 4.2 🟡 MEDIUM: Logging Configuration

Use `logging` module instead of `print()`:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Usage
logger.info("Crawling started")
logger.warning("HTTP 404")
logger.error("Failed to download")
```

---

### 4.3 🟢 LOW: Type Hints

Add type hints for clarity:

```python
from typing import Set, List, Dict, Optional

def is_pdf(url: str) -> bool:
    """Check if URL is a PDF."""
    ...

def should_keep(url: str) -> bool:
    """Check if URL should be kept."""
    ...

def safe_filename(url: str) -> str:
    """Generate safe filename from URL."""
    ...
```

---

## 5. Implementation Priority

### Phase 1.1 (Critical - Do First)
1. Query string handling (crawler + filter)
2. Domain normalization (crawler)
3. PDF validation (ingestor)

### Phase 1.2 (High Priority - Do Soon)
1. URL normalization / deduplication
2. Better error handling
3. Input/output validation

### Phase 1.3 (Medium - Nice to Have)
1. Statistics tracking
2. Seed file validation
3. Better logging

### Phase 2 (Future)
1. Parallel downloads
2. Configuration files
3. Database storage

---

## Testing Suggestions

Add simple tests to verify improvements:

```python
# test_improvements.py
def test_is_pdf_with_query_string():
    assert is_pdf("https://example.com/policy.pdf?v=1")
    assert is_pdf("https://example.com/policy.pdf#page=1")

def test_domain_normalization():
    assert same_domain("https://example.com", "https://www.example.com")
    assert same_domain("https://www.qbe.com", "https://qbe.com")

def test_safe_filename():
    assert safe_filename("https://x.com/My Policy.pdf").startswith("my_")
    assert safe_filename("https://x.com/policy.pdf?v=1").endswith(".pdf")

def test_should_keep():
    assert should_keep("policy.pdf")
    assert not should_keep("claim-form.pdf")

# Run tests
if __name__ == "__main__":
    test_is_pdf_with_query_string()
    test_domain_normalization()
    test_safe_filename()
    test_should_keep()
    print("✅ All tests passed")
```

---

## Summary

| Issue | Severity | Effort | Impact |
|-------|----------|--------|--------|
| Query string handling | 🔴 Critical | Low | High |
| Domain normalization | 🔴 Critical | Low | High |
| PDF validation | 🔴 Critical | Medium | High |
| URL deduplication | 🟠 High | Medium | High |
| Error handling | 🟠 High | Low | High |
| Statistics tracking | 🟡 Medium | Low | Medium |
| Logging | 🟡 Medium | Low | Medium |
| Type hints | 🟢 Low | Low | Low |

**Recommendation:** Implement critical and high-priority items before Phase 1 production.

