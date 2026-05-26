#!/usr/bin/env python3
"""Sync Zotero group library → bibliography/reference.bib

Uses Zotero API directly with format=bibtex for clean export.
Reads ZOTERO_API_KEY, ZOTERO_GROUP_ID, BIBLIOGRAPHY_BIB_PATH from .env.
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("ZOTERO_API_KEY")
GROUP_ID = os.environ.get("ZOTERO_GROUP_ID")
BIB_PATH = Path(os.environ.get("BIBLIOGRAPHY_BIB_PATH", "bibliography/reference.bib"))

if not API_KEY or not GROUP_ID:
    print("ERROR: ZOTERO_API_KEY and ZOTERO_GROUP_ID must be set in .env")
    sys.exit(1)

BASE_URL = f"https://api.zotero.org/groups/{GROUP_ID}"
HEADERS = {"Zotero-API-Key": API_KEY}


def fetch_bibtex_chunk(start=0, limit=100):
    """Fetch one page of items in BibTeX format."""
    url = f"{BASE_URL}/items"
    params = {
        "format": "bibtex",
        "limit": limit,
        "start": start,
        "itemType": "-attachment || -note",
    }
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.text, int(resp.headers.get("Total-Results", 0))


def main():
    print(f"Fetching BibTeX from Zotero group {GROUP_ID}...")

    first_chunk, total = fetch_bibtex_chunk(0, 100)
    print(f"Total items in library: {total}")

    all_bibtex = [first_chunk]

    start = 100
    while start < total:
        chunk, _ = fetch_bibtex_chunk(start, 100)
        if chunk.strip():
            all_bibtex.append(chunk)
        start += 100

    combined = "% Bibliography (synced from Zotero)\n\n"
    combined += "\n".join(all_bibtex)
    combined = combined.rstrip() + "\n"

    BIB_PATH.write_text(combined, encoding="utf-8")
    print(f"Written {total} entries to {BIB_PATH}")


if __name__ == "__main__":
    main()
