import os

INPUT_FILE = "urls.txt"
OUTPUT_FILE = "policy_urls.txt"
FILTERED_FILE = "filtered_out_urls.txt"

KEEP_KEYWORDS = [
    "policy",
    "pds",
    "product-disclosure",
    "tmd",
    "policy-wording"
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
    "authority"
]

def should_keep(url):
    u = url.lower()
    if any(d in u for d in DROP_KEYWORDS):
        return False
    return any(k in u for k in KEEP_KEYWORDS)

def main():
    if not os.path.exists(INPUT_FILE):
        print("❌ urls.txt not found")
        return

    kept, dropped = 0, 0

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        urls = [l.strip() for l in f if l.strip()]

    for url in urls:
        if should_keep(url):
            with open(OUTPUT_FILE, "a", encoding="utf-8") as out:
                out.write(url + "\n")
            kept += 1
        else:
            with open(FILTERED_FILE, "a", encoding="utf-8") as out:
                out.write(url + "\n")
            dropped += 1

    print(f"✅ Filter complete: kept {kept}, dropped {dropped}")

if __name__ == "__main__":
    main()
