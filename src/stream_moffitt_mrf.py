"""
Streams Moffitt Cancer Center's official 464 MB CMS v3.0.0 MRF CSV file directly over HTTPS.
Filters line-by-line for our target oncology infusion HCPCS J-codes (Keytruda, Opdivo, etc.)
and saves only the oncology records to data/raw/real_moffitt_oncology_mrf.csv.
"""

import os
import csv
import requests

os.makedirs("data/raw", exist_ok=True)

MOFFITT_URL = "https://eforms.moffitt.org/Moffittcancercenter_standardcharges/593238634_H.-Lee-Moffitt-Cancer-Center-and-Research-Institute-Hospital,-Inc._standardcharges.csv"

# Target Oncology J-codes
TARGET_CODES = {
    "J9271", "J9299", "J9355", "J9035", "J9312", 
    "J9145", "J9022", "J9228", "J2505", "J9305",
    "J9041", "J9171", "J9267", "J9190", "J9263"
}

def stream_and_filter_moffitt():
    print(f"Connecting to Moffitt live MRF stream:\n{MOFFITT_URL}\n")
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(MOFFITT_URL, headers=headers, stream=True)
    if response.status_code != 200:
        print(f"Failed with status code: {response.status_code}")
        return

    out_file = "data/raw/real_moffitt_oncology_mrf.csv"
    matched_count = 0
    header_row = None
    
    # decode_unicode=True ensures lines are strings, but we wrap in str() to guarantee string mode
    lines = response.iter_lines(decode_unicode=True)
    
    line_idx = 0
    with open(out_file, "w", newline="", encoding="utf-8") as f_out:
        writer = None
        
        for raw_line in lines:
            line_idx += 1
            if not raw_line:
                continue
                
            # Guarantee line is a string (handle if received as bytes)
            line = raw_line.decode('utf-8', errors='ignore') if isinstance(raw_line, bytes) else raw_line
                
            # Line 3 is the column header row
            if line_idx == 3:
                header_row = list(csv.reader([line]))[0]
                writer = csv.writer(f_out)
                writer.writerow(header_row)
                print(f"Captured Header Row with {len(header_row)} columns.")
                continue
                
            if line_idx < 3:
                continue

            # Check if any target J-code is in this line before heavy parsing
            if any(code in line for code in TARGET_CODES):
                row = list(csv.reader([line]))[0]
                writer.writerow(row)
                matched_count += 1
                if matched_count % 25 == 0:
                    print(f"  Matched {matched_count} oncology pricing lines (processed {line_idx:,} lines)...")

    print(f"\nDone! Extracted {matched_count} oncology pricing records from Moffitt Cancer Center.")
    print(f"Saved cleanly to: {out_file}")

if __name__ == "__main__":
    stream_and_filter_moffitt()
