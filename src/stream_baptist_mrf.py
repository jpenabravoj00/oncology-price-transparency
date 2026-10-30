"""
Streams and extracts real oncology pricing records from Baptist Health South Florida
(South Miami Hospital) directly from their official ZIP archive, capturing the exact CMS line 3 header.
"""

import os
import csv
import io
import zipfile
import requests

os.makedirs("data/raw", exist_ok=True)

BAPTIST_URL = "https://baptisthealth.net/-/media/Documents/Patient-Resources/Patient-Pricing/Apr-2026/590872594_south-miami-hospital_standardcharges.zip"

TARGET_CODES = {
    "J9271", "J9299", "J9355", "J9035", "J9312", 
    "J9145", "J9022", "J9228", "J2505", "J9305",
    "J9041", "J9171", "J9267", "J9190", "J9263"
}

def stream_and_filter_baptist():
    print(f"Downloading Baptist Health ZIP archive from:\n{BAPTIST_URL}\n")
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(BAPTIST_URL, headers=headers, timeout=40)
    
    if r.status_code != 200:
        print(f"Failed with status code: {r.status_code}")
        return

    out_file = "data/raw/real_baptist_oncology_mrf.csv"
    matched_count = 0
    
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        csv_name = [n for n in z.namelist() if n.endswith(".csv")][0]
        print(f"Processing uncompressed stream of: {csv_name} ...")
        
        with z.open(csv_name) as f_in, open(out_file, "w", newline="", encoding="utf-8") as f_out:
            reader = io.TextIOWrapper(f_in, encoding="utf-8", errors="ignore")
            writer = csv.writer(f_out)
            
            line_idx = 0
            for line in reader:
                line_idx += 1
                
                # Line 3 is the exact column header row
                if line_idx == 3:
                    header_row = list(csv.reader([line]))[0]
                    writer.writerow(header_row)
                    print(f"Captured Header Row with {len(header_row)} columns at line 3.")
                    continue
                    
                if line_idx < 3:
                    continue

                if any(code in line for code in TARGET_CODES):
                    row = list(csv.reader([line]))[0]
                    writer.writerow(row)
                    matched_count += 1
                    if matched_count % 500 == 0:
                        print(f"  Matched {matched_count:,} oncology records (processed {line_idx:,} lines)...")

    print(f"\nDone! Extracted {matched_count:,} oncology pricing records from Baptist Health South Florida.")
    print(f"Saved cleanly to: {out_file}")

if __name__ == "__main__":
    stream_and_filter_baptist()
