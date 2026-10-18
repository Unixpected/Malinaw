"""Download the archive of DPWH Transparency Portal project data.

Source: csiiiv/dpwh-transparency-data-api-scraper (base-data/base-data-json.tar.xz), which
holds the portal's project list as JSON pages. The archive does not state when it was collected.
"""
import json, os, requests

cfg = json.load(open("config.json"))
os.makedirs(os.path.dirname(cfg["archive_path"]), exist_ok=True)
with requests.get(cfg["archive_url"], stream=True, timeout=300) as r:
    r.raise_for_status()
    with open(cfg["archive_path"], "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
print(f"Saved {os.path.getsize(cfg['archive_path']):,} bytes")
