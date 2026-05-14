#!/usr/bin/env python3
"""
Verify all bib entries against OpenAlex, Semantic Scholar, and OPAC SBN.
Generates a structured audit report.
"""
import json, re, urllib.request, urllib.parse, subprocess, os, sys, time

BIB_FILE = os.environ.get("BIBLIOGRAPHY_BIB_PATH", "bibliography/reference.bib")
OPENALEX_MAILTO = os.environ.get("OPENALEX_MAILTO", "")

CLI_DIRS = {
    "openalex": "openalex-pp-cli",
    "semantic-scholar": "semantic-scholar-pp-cli",
    "opac-sbn": "opac-sbn-pp-cli",
}

def parse_bib(path):
    entries = []
    with open(path) as f:
        content = f.read()
    for m in re.finditer(r'@(\w+)\{(\w+),', content):
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
            "key": key, "kind": m.group(1),
            "title": title.group(1).strip() if title else "",
            "year": year.group(1) if year else "",
            "author": author.group(1).strip() if author else "",
        })
    return entries

def query_openalex(title, mailto):
    params = urllib.parse.urlencode({"search": title, "mailto": mailto, "per_page": 3})
    url = f"https://api.openalex.org/works?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "bibliography-verify/1.0"})
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
    if "error" in result:
        return "error", result["error"]
    
    if source == "openalex":
        meta = result.get("meta", {})
        count = meta.get("count", 0)
        if count == 0:
            return "not_found", ""
        best = result.get("results", [])[0]
        score = best.get("relevance_score", 0)
        title = best.get("title", "")
        year = str(best.get("publication_year", ""))
        authors = [a.get("author", {}).get("display_name", "") for a in best.get("authorships", [])]
        oa_id = best.get("id", "")
    elif source == "semantic-scholar":
        data = result.get("data", [])
        if not data:
            return "not_found", ""
        best = data[0]
        score = 100  # no relevance score in S2, use heuristics
        title = best.get("title", "")
        year = str(best.get("year", ""))
        authors = [a.get("name", "") for a in best.get("authors", [])]
        oa_id = f"https://api.semanticscholar.org/graph/v1/paper/{best.get('paperId','')}"
    elif source == "opac":
        num = result.get("numFound", 0)
        if num == 0:
            return "not_found", ""
        recs = result.get("briefRecords", [])
        if not recs:
            return "not_found", ""
        best = recs[0]
        score = 50
        title = best.get("titolo", "")
        year = best.get("pubblicazione", "")
        authors = [best.get("autorePrincipale", "")]
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
        year_ok = bib_year in year
    else:
        year_ok = year == bib_year
    
    confidence = "low"
    if title_overlap > 0.6 and author_ok and year_ok:
        confidence = "high"
    elif title_overlap > 0.4 and (author_ok or year_ok):
        confidence = "medium"
    elif title_overlap > 0.3:
        confidence = "low"
    
    return confidence, {"title": title, "year": year, "authors": authors, "id": oa_id, "score": score}

def main():
    entries = parse_bib(BIB_FILE)
    report = {}
    
    for e in entries:
        key = e["key"]
        report[key] = {"bib": e, "sources": {}}
        
        # OpenAlex
        if OPENALEX_MAILTO:
            r = query_openalex(e["title"], OPENALEX_MAILTO)
            status, info = score_match(e, r, "openalex")
            report[key]["sources"]["openalex"] = {"status": status, "info": info}
            time.sleep(0.1)
        
        # Semantic Scholar
        r = query_semantic_scholar(e["title"])
        status, info = score_match(e, r, "semantic-scholar")
        report[key]["sources"]["semantic-scholar"] = {"status": status, "info": info}
        time.sleep(0.3)
        
        # OPAC SBN (only for books/misc)
        if e["kind"] in ("book", "misc", "incollection", "techreport"):
            r = query_opac(e["title"])
            status, info = score_match(e, r, "opac")
            report[key]["sources"]["opac-sbn"] = {"status": status, "info": info}
            time.sleep(0.2)
    
    # Print report
    print(f"\n{'='*80}")
    print(f"BIBLIOGRAPHY VERIFICATION REPORT")
    print(f"{'='*80}")
    for key, data in report.items():
        e = data["bib"]
        print(f"\n{key}: {e['title'][:60]}")
        best_status = "not_found"
        best_source = None
        for src, s in data["sources"].items():
            status = s["status"]
            if status == "high":
                best_status = "high"
                best_source = src
            elif status == "medium" and best_status != "high":
                best_status = "medium"
                best_source = src
            elif status == "low" and best_status not in ("high", "medium"):
                best_status = "low"
                best_source = src
            icon = {"high": "✅", "medium": "🔶", "low": "⚠️", "not_found": "❌", "error": "⚠️"}.get(status, "?")
            info = s.get("info", {})
            if isinstance(info, dict):
                print(f"  {icon} {src}: {info.get('title','')[:60]}")
                if info.get("id"):
                    print(f"     ID: {info['id']}")
            else:
                print(f"  {icon} {src}: {status}")

if __name__ == "__main__":
    main()
