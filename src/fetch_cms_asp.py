"""
Fetches the official CMS Medicare Part B Average Sales Price (ASP) file directly from CMS.gov.
Uses the verified CMS URL: https://www.cms.gov/medicare/payment/part-b-drugs/asp-pricing-files
"""

import os
import io
import re
import zipfile
import requests
import pandas as pd

os.makedirs("data/raw", exist_ok=True)

HUB_URL = "https://www.cms.gov/medicare/payment/part-b-drugs/asp-pricing-files"
BASE_URL = "https://www.cms.gov"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
}

def download_official_cms_asp():
    print(f"Connecting to official CMS Part B Drugs Hub:\n{HUB_URL}\n")
    resp = requests.get(HUB_URL, headers=HEADERS, timeout=15)
    
    if resp.status_code != 200:
        print(f"Failed to load CMS Hub: status {resp.status_code}")
        return

    # Extract all zip links that represent the quarterly ASP Pricing Files
    links = re.findall(r'href=[\"\'](/files/zip/[^\"\']+\.zip|https://[^\"\']+\.zip)[\"\']', resp.text)
    pricing_zips = [l for l in links if "asp-pricing-file" in l.lower() or "payment-limit" in l.lower()]
    
    if not pricing_zips:
        print("No pricing zip files matched.")
        return

    # Select the most recent quarterly file
    latest_path = pricing_zips[0]
    full_url = latest_path if latest_path.startswith("http") else f"{BASE_URL}{latest_path}"
    
    print(f"Found active official CMS quarterly pricing file:\n{full_url}\n")
    print("Downloading file from CMS.gov ...")
    
    r = requests.get(full_url, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        print(f"Download failed with HTTP {r.status_code}")
        return
        
    print(f"Download complete ({len(r.content):,} bytes). Extracting contents...")
    
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        for filename in z.namelist():
            print(f" - Found inside zip: {filename}")
            if filename.lower().endswith((".csv", ".xlsx", ".xls")):
                extracted_path = os.path.join("data/raw", filename)
                with open(extracted_path, "wb") as f:
                    f.write(z.read(filename))
                print(f"Saved real CMS file to: {extracted_path}")

if __name__ == "__main__":
    download_official_cms_asp()
