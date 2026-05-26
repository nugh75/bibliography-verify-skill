#!/usr/bin/env python3
"""Import bibliography/reference.bib into Zotero group library using pyzotero.

Usage:
    .venv/bin/python .claude/skills/bibliography-verify/scripts/import_bib_to_zotero.py

Reads ZOTERO_API_KEY, ZOTERO_GROUP_ID, ZOTERO_LIBRARY_TYPE, BIBLIOGRAPHY_BIB_PATH from .env.
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from pybtex.database import parse_file
from pyzotero import zotero

load_dotenv()

API_KEY = os.environ.get("ZOTERO_API_KEY")
GROUP_ID = os.environ.get("ZOTERO_GROUP_ID")
LIBRARY_TYPE = os.environ.get("ZOTERO_LIBRARY_TYPE", "group")
BIB_PATH = Path(os.environ.get("BIBLIOGRAPHY_BIB_PATH", "bibliography/reference.bib"))

if not API_KEY or not GROUP_ID:
    print("ERROR: ZOTERO_API_KEY and ZOTERO_GROUP_ID must be set in .env")
    sys.exit(1)


def main():
    print(f"Parsing {BIB_PATH}...")
    bib = parse_file(str(BIB_PATH))

    print(f"Connecting to Zotero {LIBRARY_TYPE} {GROUP_ID}...")
    zot = zotero.Zotero(GROUP_ID, LIBRARY_TYPE, API_KEY)

    # Clear existing items in group
    existing = zot.items(limit=100)
    if existing:
        print(f"Removing {len(existing)} existing items...")
        for item in existing:
            zot.delete_item(item)
            time.sleep(0.2)

    # Type map: BibTeX → Zotero itemType
    type_map = {
        "article": "journalArticle",
        "book": "book",
        "inbook": "bookSection",
        "incollection": "bookSection",
        "inproceedings": "conferencePaper",
        "misc": "document",
        "techreport": "report",
        "unpublished": "manuscript",
    }

    imported = 0
    failed = 0
    for entry_key in bib.entries:
        entry = bib.entries[entry_key]
        te = entry.type.lower()
        fields = entry.fields
        item_type = type_map.get(te, "document")

        print(f"  [{entry_key}] ({item_type}) {fields.get('title','?')[:60]}...")

        try:
            template = zot.item_template(item_type)
        except Exception as e:
            print(f"    Could not get template for {item_type}: {e}")
            template = {}

        # Title
        if "title" in fields:
            template["title"] = fields["title"]

        # Creators
        template["creators"] = []
        person_field_map = {"author": "author", "editor": "editor"}
        for role, zrole in person_field_map.items():
            if role in entry.persons:
                for person in entry.persons[role]:
                    first = " ".join(person.first_names + person.middle_names)
                    last = " ".join(person.last_names)
                    template["creators"].append({
                        "creatorType": zrole,
                        "firstName": first,
                        "lastName": last,
                    })

        # Field maps per item type
        field_map = {
            "journalArticle": {
                "journal": "publicationTitle",
                "volume": "volume",
                "number": "issue",
                "pages": "pages",
                "year": "date",
                "doi": "DOI",
                "issn": "ISSN",
                "note": "extra",
                "url": "url",
            },
            "book": {
                "publisher": "publisher",
                "address": "place",
                "year": "date",
                "edition": "edition",
                "isbn": "ISBN",
                "url": "url",
                "note": "extra",
            },
            "bookSection": {
                "booktitle": "publicationTitle",
                "publisher": "publisher",
                "address": "place",
                "pages": "pages",
                "year": "date",
                "isbn": "ISBN",
                "url": "url",
                "note": "extra",
            },
            "report": {
                "publisher": "publisher",
                "number": "reportNumber",
                "year": "date",
                "url": "url",
                "note": "extra",
            },
            "document": {
                "publisher": "publisher",
                "year": "date",
                "url": "url",
                "note": "extra",
            },
        }

        fm = field_map.get(item_type, field_map["document"])
        for bib_f, zot_f in fm.items():
            if bib_f in fields:
                val = fields[bib_f]
                if bib_f == "year":
                    try:
                        val = str(int(val))
                    except ValueError:
                        val = str(val)
                template[zot_f] = val

        if "extra" in template and not template["extra"]:
            del template["extra"]

        try:
            zot.create_items([template])
            imported += 1
        except Exception as e:
            failed += 1
            print(f"    FAILED: {e}")

        time.sleep(0.3)

    print(f"\nDone. Imported: {imported}, Failed: {failed} / Total: {len(bib.entries)}")


if __name__ == "__main__":
    main()
