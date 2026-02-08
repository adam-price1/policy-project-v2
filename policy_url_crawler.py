import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import time

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
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def append_line(path, line):
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def is_pdf(url):
    return url.lower().endswith(".pdf")

def same_domain(seed, url):
    return urlparse(seed).netloc == urlparse(url).netloc

def is_allowed_path(url):
    u = url.lower()

    # block obvious non-insurance areas
    if any(d in u for d in DENY_PATH_KEYWORDS):
        return False

    # must contain insurance-related keywords
    return any(k in u for k in ALLOWED_PATH_KEYWORDS)

# =========================
# MAIN CRAWLER
# =========================

def crawl():
    if not os.path.exists(SEED_FILE):
        print(f"❌ ERROR: Seed file not found: {SEED_FILE}")
        return

    seeds = load_lines(SEED_FILE)
    seen_pages = load_lines(SEEN_PAGES_FILE)
    seen_pdfs = load_lines(SEEN_PDFS_FILE)

    print("🚀 Starting insurance policy crawl")
    print(f"🌱 Seeds loaded: {len(seeds)}")
    print(f"📄 Seen pages: {len(seen_pages)}")

    for seed in seeds:
        domain = urlparse(seed).netloc
        pages_crawled = 0
        queue = [seed]

        while queue and pages_crawled < MAX_PAGES_PER_DOMAIN:
            url = queue.pop(0)

            if url in seen_pages:
                continue

            if not same_domain(seed, url):
                continue

            seen_pages.add(url)
            append_line(SEEN_PAGES_FILE, url)

            pages_crawled += 1
            print(f"🔍 Crawling ({pages_crawled}): {url}")

            try:
                r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                if r.status_code != 200:
                    print(f"  ⚠️ HTTP {r.status_code}")
                    continue

                soup = BeautifulSoup(r.text, "html.parser")

                for link in soup.find_all("a", href=True):
                    href = link["href"].strip()
                    full_url = urljoin(url, href)

                    # PDF handling
                    if is_pdf(full_url):
                        if full_url not in seen_pdfs:
                            seen_pdfs.add(full_url)
                            append_line(SEEN_PDFS_FILE, full_url)
                            append_line(URL_OUTPUT_FILE, full_url)
                            print(f"  📄 POLICY PDF FOUND: {full_url}")
                        continue

                    # page crawl decision
                    if is_allowed_path(full_url) and full_url not in seen_pages:
                        queue.append(full_url)

                time.sleep(REQUEST_DELAY)

            except requests.exceptions.RequestException as e:
                print(f"  ⚠️ Connection error: {e}")
                continue

    print("✅ Crawl finished")

# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    crawl()
