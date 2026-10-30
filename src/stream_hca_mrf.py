"""
Streams and extracts real oncology pricing records from HCA Florida Memorial Hospital
directly from their 452 MB CMS v3.0.0 JSON file on Azure Blob Storage.
Uses ijson to parse standard_charge_information.item incrementally.
"""

import os
import csv
import requests
import ijson

os.makedirs("data/raw", exist_ok=True)

HCA_URL = "https://stctrprodsnsvc00455826e6.blob.core.windows.net/pt-final-posting-files/59-3283127_HCA-FLORIDA-MEMORIAL-HOSPITAL_standardcharges.json?si=dpx-pt-json-access-policy&spr=https&sv=2026-02-06&sr=c&sig=ks%2BgfAjyEHlZmeP2PYJ%2F9NpMuCoRStjTb2bhIy9Y6LM%3D"

TARGET_CODES = {
    "J9271", "J9299", "J9355", "J9035", "J9312", 
    "J9145", "J9022", "J9228", "J2505", "J9305",
    "J9041", "J9171", "J9267", "J9190", "J9263"
}

def stream_and_filter_hca():
    print(f"Connecting to HCA Florida 452 MB JSON stream on Azure Blob:\n{HCA_URL[:100]}...\n")
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(HCA_URL, headers=headers, stream=True)
    
    if r.status_code != 200:
        print(f"Failed with status code: {r.status_code}")
        return

    out_file = "data/raw/real_hca_oncology_mrf.csv"
    matched_count = 0
    
    print("Streaming JSON items from 'standard_charge_information.item'...")
    
    with open(out_file, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow([
            "hospital_name", "description", "code", "setting", 
            "gross_charge", "discounted_cash", "payer_name", "plan_name", "negotiated_rate"
        ])
        
        try:
            items = ijson.items(r.raw, "standard_charge_information.item")
            for item in items:
                codes_info = item.get("code_information", [])
                item_codes = [str(c.get("code")).strip() for c in codes_info if isinstance(c, dict)]
                
                matched = [c for c in item_codes if c in TARGET_CODES]
                if matched:
                    desc = item.get("description", "")
                    code_matched = matched[0]
                    charges_list = item.get("standard_charges", [])
                    
                    for sc in charges_list:
                        setting = sc.get("setting", "")
                        gross = sc.get("gross_charge", "")
                        cash = sc.get("discounted_cash", "")
                        payers = sc.get("payers_information", [])
                        
                        if payers:
                            for p in payers:
                                writer.writerow([
                                    "HCA Florida Memorial Hospital",
                                    desc,
                                    code_matched,
                                    setting,
                                    gross,
                                    cash,
                                    p.get("payer_name", ""),
                                    p.get("plan_name", ""),
                                    p.get("standard_charge_dollar", "")
                                ])
                                matched_count += 1
                        else:
                            writer.writerow([
                                "HCA Florida Memorial Hospital",
                                desc,
                                code_matched,
                                setting,
                                gross,
                                cash,
                                "", "", ""
                            ])
                            matched_count += 1
                            
                    if matched_count % 100 == 0:
                        print(f"  Captured {matched_count} HCA oncology price points...")
        except Exception as e:
            print(f"Streaming parse completed or stopped: {e}")

    print(f"\nDone! Extracted {matched_count} oncology records from HCA Florida Memorial Hospital.")
    print(f"Saved cleanly to: {out_file}")

if __name__ == "__main__":
    stream_and_filter_hca()
