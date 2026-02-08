import os
import json
import requests
from datetime import datetime

INPUT_FILE = "policy_urls.txt"
RAW_DIR = "raw_documents"
META_DIR = "metadata"

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(META_DIR, exist_ok=True)

def safe_filename(url):
    return url.split("/")[-1].replace("?", "_")

def main():
    if not os.path.exists(INPUT_FILE):
        print("❌ policy_urls.txt not found")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        urls = [l.strip() for l in f if l.strip()]

    for url in urls:
        filename = safe_filename(url)
        pdf_path = os.path.join(RAW_DIR, filename)
        meta_path = os.path.join(META_DIR, filename + ".json")

        if os.path.exists(pdf_path):
            continue

        print(f"⬇️ Downloading {filename}")
        try:
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                print("  ⚠️ Download failed")
                continue

            with open(pdf_path, "wb") as f:
                f.write(r.content)

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

            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            print("  ⚠️ Error:", e)

    print("✅ Ingestion complete")

if __name__ == "__main__":
    main()
