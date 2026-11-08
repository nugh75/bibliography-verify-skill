#!/usr/bin/env python3
"""
Verify all bib entries against OpenAlex, Semantic Scholar, and OPAC SBN.
Generates a structured audit report.
"""
import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request

BIB_FILE = os.environ.get("BIBLIOGRAPHY_BIB_PATH", "bibliography/reference.bib")
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY", "")

SOURCES = ("openalex", "semantic-scholar", "opac-sbn")
OPAC_KINDS = {"book", "misc", "incollection", "techreport"}


def parse_bib(path):
    entries = []
    with open(path, encoding="utf-8") as f:
        content = f.read()
    for m in re.finditer(r'@(\w+)\{\s*([^\s,{}]+)\s*,', content):
        key = m.group(2)
        start = content.index('{', m.start()) + 1
        depth, pos = 1, start
        while depth > 0 and pos < len(content):
            if content[pos] == '{': depth += 1
            elif content[pos] == '}': depth -= 1
            pos += 1
        body = content[start:pos-1]
        title = re.search(r'title\s*=\s*\{(.*?)\}', body, re.DOTALL)
        year = re.search(r'year\s*=\s*\{(\d+)\}', body)
        author = re.search(r'author\s*=\s*\{(.*?)\}', body, re.DOTALL)
        entries.append({
            "key": key, "kind": m.group(1).lower(),
            "title": title.group(1).strip() if title else "",
            "year": year.group(1) if year else "",
            "author": author.group(1).strip() if author else "",
        })
    return entries

def query_openalex(title):
    params = urllib.parse.urlencode({"search": title, "per_page": 3})
    url = f"https://api.openalex.org/works?{params}"
    headers = {"User-Agent": "bibliography-verify/1.0"}
    if OPENALEX_API_KEY:
        headers["Authorization"] = f"Bearer {OPENALEX_API_KEY}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def query_semantic_scholar(title):
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.parse.quote(title)}&limit=3&fields=title,year,authors,venue,externalIds"
    req = urllib.request.Request(url, headers={"User-Agent": "bibliography-verify/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def query_opac(title):
    url = f"http://opac.sbn.it/opacmobilegw/search.json?any={urllib.parse.quote(title[:60])}&type=0&start=0&rows=3"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def score_match(bib_entry, result, source):
    """Score how well a result matches the bib entry."""
    if not isinstance(result, dict):
        return "error", "Unexpected response format"
    if "error" in result:
        return "error", str(result["error"])

    items_key = {"openalex": "results", "semantic-scholar": "data", "opac": "briefRecords"}[source]
    if source == "openalex":
        meta = result.get("meta")
        reported_count = meta.get("count") if isinstance(meta, dict) else None
    else:
        reported_count = result.get("total" if source == "semantic-scholar" else "numFound")
    items = result.get(items_key)
    if reported_count == 0 and not items:
        return "not_found", ""
    if not isinstance(items, list) or (not items and reported_count):
        return "error", f"Missing or incomplete response field: {items_key}"
    if not items:
        return "not_found", ""
    best = items[0]
    if not isinstance(best, dict):
        return "error", f"Invalid record in response field: {items_key}"

    if source == "openalex":
        score = best.get("relevance_score", 0)
        title = best.get("title") or ""
        year = str(best.get("publication_year", ""))
        authors = [(a.get("author") or {}).get("display_name") or "" for a in (best.get("authorships") or [])]
        oa_id = best.get("id", "")
    elif source == "semantic-scholar":
        score = 100  # no relevance score in S2, use heuristics
        title = best.get("title") or ""
        year = str(best.get("year", ""))
        authors = [a.get("name") or "" for a in (best.get("authors") or [])]
        oa_id = f"https://api.semanticscholar.org/graph/v1/paper/{best.get('paperId','')}"
    elif source == "opac":
        score = 50
        title = best.get("titolo") or ""
        year = str(best.get("pubblicazione") or "")
        authors = [best.get("autorePrincipale") or ""]
        oa_id = f"BID: {best.get('codiceIdentificativo', '')}"
    
    bib_title = bib_entry["title"].lower()
    bib_year = bib_entry["year"]
    bib_author = bib_entry["author"].split(" and ")[0].split(",")[0].strip().lower() if bib_entry["author"] else ""
    
    # Check title similarity
    title_words = set(bib_title.split()[:5])
    result_words = set(title.lower().split()[:5])
    title_overlap = len(title_words & result_words) / max(len(title_words), 1)
    
    # Check author
    author_ok = any(bib_author in a.lower() for a in authors) if bib_author else False
    
    # Check year
    year_ok = False
    if source == "opac":
        year_ok = bool(bib_year and bib_year in year)
    else:
        year_ok = year == bib_year
    
    confidence = "low"
    if title_overlap > 0.6 and author_ok and year_ok:
        confidence = "high"
    elif title_overlap > 0.4 and (author_ok or year_ok):
        confidence = "medium"
    
    return confidence, {"title": title, "year": year, "authors": authors, "id": oa_id, "score": score}

def audit_entry(entry, selected="all"):
    results = {}
    for source in SOURCES:
        if selected not in ("all", source):
            status, info = "not_queried", "Source not selected"
        elif not entry["title"]:
            status, info = "not_queried", "Entry has no title"
        elif source == "opac-sbn" and entry["kind"] not in OPAC_KINDS:
            status, info = "not_queried", "Entry type outside the OPAC search scope"
        elif source == "openalex":
            status, info = score_match(entry, query_openalex(entry["title"]), source)
            time.sleep(0.1)
        elif source == "semantic-scholar":
            status, info = score_match(entry, query_semantic_scholar(entry["title"]), source)
            time.sleep(0.3)
        else:
            status, info = score_match(entry, query_opac(entry["title"]), "opac")
            time.sleep(0.2)
        results[source] = {"status": status, "info": info}
    return results


def main(argv=None, *, default_source="all"):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bib", default=BIB_FILE, help="Path to the BibTeX file")
    parser.add_argument("--source", choices=("all", *SOURCES), default=default_source)
    parser.add_argument("--key", help="Verify a single BibTeX key")
    args = parser.parse_args(argv)
    entries = parse_bib(args.bib)
    if args.key:
        entries = [entry for entry in entries if entry["key"] == args.key]
        if not entries:
            parser.error(f"Unknown BibTeX key: {args.key}")

    print("BIBLIOGRAPHY VERIFICATION REPORT")
    for entry in entries:
        print(f"\n{entry['key']}: {entry['title']}")
        for source, result in audit_entry(entry, args.source).items():
            status, info = result["status"], result["info"]
            if isinstance(info, dict):
                detail = f"{info['title']} | {info['year']} | {', '.join(info['authors'])}"
                if info["id"]:
                    detail += f" | {info['id']}"
            else:
                detail = info
            print(f"  {source}: {status}" + (f" — {detail}" if detail else ""))


if __name__ == "__main__":
    main()
