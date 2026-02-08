# Insurance Policy PDF Ingestion Pipeline – Phase 1

**Project:** PolicyCheck – Insurance Policy Data Ingestion  
**Version:** 2 (Production-Ready)  
**Status:** ✅ Phase 1 complete  
**Last Updated:** 2026-02-08

---

## Overview

This is a **deterministic, auditable pipeline** for discovering, filtering, and ingesting insurance policy PDFs from official insurer websites. Phase 1 focuses on **reliable collection**, not interpretation.

**Three-step pipeline:**
1. **Crawl** — Discover PDFs from insurer sites
2. **Filter** — Keep only real policies, reject junk
3. **Ingest** — Download, validate, and store PDFs with metadata

---

## Key Features

### Crawling (`policy_url_crawler.py`)
- ✅ Recursive crawl from seed insurer URLs
- ✅ Domain-boundary enforcement (stay on same insurer site)
- ✅ Path-based filtering (allowed/deny keywords)
- ✅ Resume-safe (tracks seen pages and PDFs)
- ✅ Polite crawling (0.5s delay between requests)

### Filtering (`policy_url_filter.py`)
- ✅ URL-based classification using keyword lists
- ✅ Whitelist keywords (must have: policy, pds, product-disclosure, etc.)
- ✅ Blacklist keywords (must not have: form, claim, guide, etc.)
- ✅ Output audit trail (rejected URLs saved)
- ✅ Simple, deterministic logic (no ML/heuristics)

### Ingestion (`admin_pdf_ingestor_v2.py`)
- ✅ Sequential downloads (safe, predictable)
- ✅ Resume-safe (skips existing PDFs)
- ✅ Metadata JSON per file (URL, timestamp, status)
- ✅ Simple error logging (writes to console)
- ✅ Placeholder fields for future classification

---

## Quick Start

### 1. Install
```bash
pip install -r requirements.txt
```

### 2. Crawl
```bash
python policy_url_crawler.py
```
Output: `urls.txt` (all discovered PDFs)

### 3. Filter
```bash
python policy_url_filter.py
```
Output: 
- `policy_urls.txt` (valid policies)
- `filtered_out_urls.txt` (rejected, for audit)

### 4. Ingest
```bash
python admin_pdf_ingestor_v2.py
```
Output:
- `raw_documents/` (downloaded PDFs)
- `metadata/` (JSON metadata files)

### 5. Inspect Results
```bash
# View a metadata file
cat metadata/policy_001.pdf.json | jq .

# Count downloads
ls -1 raw_documents/*.pdf | wc -l

# Check audit trail
cat filtered_out_urls.txt | head
```

---

## Design Principles

### Deterministic
- Same inputs always produce same outputs
- No randomization, no external APIs
- Keyword matching only (Phase 1)

### Simple & Understandable
- Three separate scripts (clear separation)
- No complex architectures
- Easy to debug and extend

### Resume-Safe
- All scripts safe to re-run
- State tracked in text files
- No data loss on failure

### Auditable
- Every URL tracked (urls.txt, filtered_out_urls.txt)
- Metadata for every PDF
- Clear rejection reasons

---

## Directory Structure

```
├── policy_url_crawler.py      # Step 1: Discover PDFs
├── policy_url_filter.py       # Step 2: Filter to real policies
├── admin_pdf_ingestor_v2.py   # Step 3: Download & store
├── seed_insurers.txt          # Starting URLs (edit this)
├── requirements.txt           # Dependencies
│
├── urls.txt                   # All discovered PDFs (generated)
├── seen_pages.txt             # Crawled pages (for resume)
├── seen_pdfs.txt              # Discovered PDFs (for resume)
├── policy_urls.txt            # Filtered, valid policies
├── filtered_out_urls.txt      # Rejected URLs (audit trail)
│
├── raw_documents/             # Downloaded PDFs
└── metadata/                  # JSON metadata files
```

---

## Configuration

### Crawler (`policy_url_crawler.py`)

Edit these at the top of the file:

```python
MAX_PAGES_PER_DOMAIN = 1000      # Max pages to crawl per insurer
REQUEST_DELAY = 0.5              # Seconds between requests (politeness)
TIMEOUT = 10                     # Request timeout
```

Path filtering keywords (edit to tune):
```python
ALLOWED_PATH_KEYWORDS = [        # Must contain at least one
    "/insurance", "/policy", "/policies", "/documents", 
    "/pds", "/product-disclosure"
]

DENY_PATH_KEYWORDS = [           # Must not contain any
    "/about/", "/careers/", "/news/", "/media/", 
    "/blog/", "/form", "/claim", ...
]
```

### Filter (`policy_url_filter.py`)

Edit keywords to tune filtering:

```python
KEEP_KEYWORDS = [                # Must contain at least one
    "policy", "pds", "product-disclosure", "tmd", "policy-wording"
]

DROP_KEYWORDS = [                # Must not contain any
    "form", "application", "claim", "guide", "fsg", 
    "brochure", "fact-sheet", "statement", "authority"
]
```

### Ingestor (`admin_pdf_ingestor_v2.py`)

Edit input/output directories:

```python
INPUT_FILE = "policy_urls.txt"   # Read URLs from this file
RAW_DIR = "raw_documents"        # Save PDFs here
META_DIR = "metadata"            # Save JSON metadata here
```

---

## Seed Insurers

Edit `seed_insurers.txt` with insurer homepages:

```
https://www.qbe.com/au
https://www.aami.com.au
https://www.suncorp.com.au
https://www.allianz.com.au
https://www.iag.com.au
https://www.nrma.com.au
https://www.aa.co.nz
https://www.ami.co.nz
https://www.vero.co.nz
https://www.tower.co.nz
https://fmgnz.co.nz
https://www.state.co.nz
https://www.aviva.co.uk
https://www.zurich.co.uk
https://www.qbe.com/uk
```

---

## Metadata Format

Each downloaded PDF gets a JSON metadata file:

```json
{
  "file_name": "policy_001.pdf",
  "source_url": "https://example.com/download/policy.pdf",
  "download_date": "2026-02-08T14:32:15.123456+00:00",
  "country": "Unknown",
  "insurer": "Unknown",
  "insurance_line": "Unknown",
  "product_name": "Unknown",
  "status": "needs_classification"
}
```

Placeholder fields (`country`, `insurer`, etc.) are for **Phase 2** when we add classification logic.

---

## What's NOT Included (Phase 1 Scope)

❌ Parallel downloads (Phase 2)  
❌ Deduplication (Phase 2)  
❌ PDF parsing/OCR (Phase 2)  
❌ AI classification (Phase 2)  
❌ Metadata extraction (Phase 2)  
❌ Database storage (Phase 2)  

Phase 1 is **collection only** — build a trusted dataset first.

---

## Troubleshooting

### "ERROR: Seed file not found"
Create `seed_insurers.txt` with insurer URLs.

### "Crawling is very slow"
- Check `REQUEST_DELAY` (default 0.5s is polite)
- Increase `MAX_PAGES_PER_DOMAIN` (default 1000)
- Increase `TIMEOUT` if servers respond slowly

### "No PDFs found"
- Check seed URLs are valid
- Verify PDFs exist at those sites
- Review `ALLOWED_PATH_KEYWORDS` (too restrictive?)
- Check `DENY_PATH_KEYWORDS` (blocking PDFs?)

### "Filter is rejecting too many URLs"
- Review `KEEP_KEYWORDS` (need more variations?)
- Review `DROP_KEYWORDS` (too aggressive?)
- Check `filtered_out_urls.txt` to see what's rejected

### "Metadata files not created"
- Check `metadata/` directory exists
- Verify write permissions
- Check console for error messages

---

## Performance Notes

### Single-Domain Crawl
- **Default settings:** ~2-5 PDFs/min per insurer (polite)
- **Fast mode:** Reduce `REQUEST_DELAY` to 0.1s
- **Slow network:** Increase `TIMEOUT` to 30s

### Filtering
- All URLs filtered in <1 second (simple keyword matching)
- Output written line-by-line (safe for large files)

### Ingestion
- **Default:** ~1-2 PDFs/min (sequential, safe)
- **Network:** Depends on PDF size and connection
- **No parallelism yet** (Phase 2 feature)

---

## Resume & Recovery

### After Crawler Interruption
```bash
# Continue crawling (skips seen_pages.txt)
python policy_url_crawler.py
```

### After Filter Interruption
```bash
# Re-run filter (regenerates output files)
python policy_url_filter.py
```

### After Ingestor Interruption
```bash
# Continue ingestion (skips existing PDFs)
python admin_pdf_ingestor_v2.py
```

All scripts are safe to re-run at any time.

---

## Data Outputs

### `urls.txt`
All discovered PDF URLs (one per line).

### `seen_pages.txt`
All crawled pages (for resume-safety).

### `seen_pdfs.txt`
All discovered PDFs (for deduplication).

### `policy_urls.txt`
Filtered, valid policy URLs only.

### `filtered_out_urls.txt`
Rejected URLs (audit trail for review).

### `raw_documents/`
Downloaded PDF files.

### `metadata/`
JSON metadata files (one per PDF).

---

## Next Steps

### Phase 2 (Planned)
- Parallel downloads for speed
- Deduplication (same policy, different versions)
- PDF parsing to extract metadata
- Basic policy type classification

### Phase 3 (Future)
- AI-assisted extraction
- Policy comparison
- Risk detection
- Country-specific handling

---

## Notes

- **Dependencies:** `requests`, `beautifulsoup4`
- **Python version:** 3.7+
- **File formats:** UTF-8 text files, JSON metadata
- **Determinism:** Same runs always produce same results
- **Safety:** No data is ever deleted, only appended

---

## Support

See included documentation:
- **QUICK_SUMMARY.md** — High-level changes
- **PHASE1_CODE_REVIEW.md** — Detailed review
- **IMPLEMENTATION_SUMMARY.md** — Change explanations
- **CODE_REVIEW_CHECKLIST.md** — Testing & deployment

---

**Version 2 is production-ready. Start with `seed_insurers.txt`, then run the three scripts in order.**
