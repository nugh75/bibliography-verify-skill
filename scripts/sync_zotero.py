#!/usr/bin/env python3
"""Sync Zotero group library → bibliography/reference.bib

Uses Zotero API JSON format and generates clean BibTeX locally,
avoiding Zotero's case-protection braces ({D}{o}) and LaTeX corruption.

Reads ZOTERO_API_KEY, ZOTERO_GROUP_ID, BIBLIOGRAPHY_BIB_PATH from .env.
"""

import os
import re
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

# BibTeX → Zotero itemType (reverse map)
BIBTEX_TYPE_MAP = {
    "journalArticle": "article",
    "book": "book",
    "conferencePaper": "inproceedings",
    "bookSection": "incollection",
    "report": "techreport",
    "document": "misc",
    "manuscript": "unpublished",
    "thesis": "phdthesis",
}

# Fields to skip when generating BibTeX
SKIP_FIELDS = {
    "key", "version", "itemType", "creators", "tags", "collections",
    "relations", "dateAdded", "dateModified", "extra", "abstractNote",
    "citationKey", "shortTitle", "language", "libraryCatalog", "callNumber",
    "rights", "url", "accessDate", "archive", "archiveLocation",
    "series", "seriesTitle", "seriesText", "section", "partNumber",
    "partTitle",
}

# Zotero JSON field → BibTeX field name
FIELD_MAP = {
    "title": "title",
    "publicationTitle": "journal",
    "bookTitle": "booktitle",
    "publisher": "publisher",
    "place": "address",
    "date": "year",
    "volume": "volume",
    "issue": "number",
    "pages": "pages",
    "edition": "edition",
    "DOI": "doi",
    "ISBN": "isbn",
    "ISSN": "issn",
    "note": "note",
    "reportNumber": "number",
    "university": "school",
    "thesisType": "type",
}


def clean_text(value: str, is_title: bool = False) -> str:
    """Clean a text value for BibTeX output."""
    if not value:
        return value
    # Remove Zotero-style escaped braces: \{{Word}} -> Word
    value = re.sub(r'\\\{\{([^{}]+)\}\}', r'\1', value)
    value = re.sub(r'\}\}([^{}])', r'\1', value)
    value = value.replace('\\}{', ':')
    # Remove Zotero-introduced \textbackslash (junk from BibTeX round-trips)
    value = re.sub(r'\{?\\textbackslash\}?', '', value)
    # Normalize braces around LaTeX commands: {{\L}} -> {\L}
    value = re.sub(r'\{\s*\{\s*(\\.+?)\s*\}\s*\}', r'{\1}', value)

    if is_title:
        # Strip redundant single-word braces from titles.
        # In BibTeX, title = {Word} already protects case; inner {W} is redundant.
        value = re.sub(r'\{([A-Za-z0-9]+)\}', r'\1', value)
        # Clean up orphaned escaped braces
        value = value.replace('\\{', '').replace('\\}', '')
        # Collapse multiple spaces
        value = re.sub(r'  +', ' ', value)
        value = re.sub(r'\s*:\s*', ': ', value)
        value = re.sub(r'\s*--\s*', '--', value)

    return value


def clean_pages(value: str) -> str:
    """Normalize page ranges."""
    if not value:
        return value
    return value.replace("--", "--")


def item_to_bibtex(item: dict) -> str:
    """Convert a Zotero JSON item to clean BibTeX string."""
    data = item.get("data", {})
    zot_type = data.get("itemType", "document")
    key = data.get("citationKey") or data.get("key", "unknown")
    bib_type = BIBTEX_TYPE_MAP.get(zot_type, "misc")

    lines = []
    lines.append(f"@{bib_type}{{{key},")

    # Authors/editors
    creators = data.get("creators", [])
    author_parts = []
    editor_parts = []
    for c in creators:
        ctype = c.get("creatorType", "author")
        first = clean_text(c.get("firstName", ""))
        last = clean_text(c.get("lastName", ""))
        if ctype == "author":
            if last and first:
                author_parts.append(f"{last}, {first}")
            elif last:
                author_parts.append(last)
        elif ctype == "editor":
            if last and first:
                editor_parts.append(f"{last}, {first}")
            elif last:
                editor_parts.append(last)

    if author_parts:
        authors_str = " and ".join(author_parts)
        lines.append(f"\tauthor = {{{authors_str}}},")
    if editor_parts:
        editors_str = " and ".join(editor_parts)
        lines.append(f"\teditor = {{{editors_str}}},")

    # Fields
    year_set = False
    for zot_field, bib_field in FIELD_MAP.items():
        raw = data.get(zot_field)
        if not raw:
            continue
        val = str(raw).strip()
        if not val:
            continue

        if zot_field == "pages":
            val = clean_pages(val)
        elif zot_field == "title":
            val = clean_text(val, is_title=True)
        elif zot_field == "date":
            year_match = re.search(r'(\d{4})', val)
            if year_match:
                val = year_match.group(1)
                year_set = True
            else:
                continue
        else:
            val = clean_text(val)

        if zot_field in SKIP_FIELDS:
            continue

        lines.append(f"\t{bib_field} = {{{val}}},")

    # If year wasn't set via date, try parsing
    if not year_set and not any("year" in l for l in lines):
        date_val = data.get("date", "")
        year_match = re.search(r'(\d{4})', str(date_val))
        if year_match:
            lines.append(f"\tyear = {{{year_match.group(1)}}},")

    lines.append("}")
    return "\n".join(lines)


def fetch_json_chunk(start=0, limit=100):
    """Fetch one page of items in JSON format."""
    url = f"{BASE_URL}/items"
    params = {
        "format": "json",
        "limit": limit,
        "start": start,
    }
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json(), int(resp.headers.get("Total-Results", 0))


def main():
    print(f"Fetching items from Zotero group {GROUP_ID}...")

    first_batch, total = fetch_json_chunk(0, 100)
    print(f"Total items in library: {total}")

    all_items = list(first_batch)

    start = 100
    while start < total:
        batch, _ = fetch_json_chunk(start, 100)
        all_items.extend(batch)
        start += 100

    if total == 0:
        print("WARNING: Zotero library is empty. Skipping write to avoid data loss.")
        return

    # Filter out attachments and notes
    items = [it for it in all_items if it.get("data", {}).get("itemType") not in ("attachment", "note")]
    print(f"Converting {len(items)} items to clean BibTeX...")

    bib_entries = []
    for item in items:
        try:
            bib_entries.append(item_to_bibtex(item))
        except Exception as e:
            key = item.get("data", {}).get("citationKey", "?")
            print(f"  WARNING: failed to convert {key}: {e}")

    combined = "% Bibliography (synced from Zotero)\n\n"
    combined += "\n\n".join(bib_entries)
    combined = combined.rstrip() + "\n"

    BIB_PATH.write_text(combined, encoding="utf-8")
    print(f"Written {len(bib_entries)} entries to {BIB_PATH}")


if __name__ == "__main__":
    main()
