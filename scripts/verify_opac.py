#!/usr/bin/env python3
"""Verify Italian bib entries against OPAC SBN."""
import json, re, urllib.request, urllib.parse, time, os, sys

BIB_FILE = os.environ.get("BIBLIOGRAPHY_BIB_PATH", "bibliography/reference.bib")

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

entries = parse_bib(BIB_FILE)
for e in entries:
    if e["kind"] not in ("book", "misc", "incollection", "techreport"):
        continue
    t = e["title"][:60]
    url = f"http://opac.sbn.it/opacmobilegw/search.json?any={urllib.parse.quote(t)}&type=0&start=0&rows=3"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as ex:
        print(f"  {e['key']} — ERROR: {ex}")
        continue
    num = data.get("numFound", 0)
    recs = data.get("briefRecords", [])
    if num == 0:
        print(f"❌ {e['key']} — NOT FOUND in OPAC SBN")
        continue
    best = recs[0]
    b_title = best.get("titolo", "")
    b_author = best.get("autorePrincipale", "")
    b_pub = best.get("pubblicazione", "")
    b_id = best.get("codiceIdentificativo", "")
    fa = e["author"].split(" and ")[0].split(",")[0].strip().lower() if e["author"] else ""
    author_ok = fa in b_author.lower() if b_author and fa else False
    title_ok = any(w.lower() in b_title.lower() for w in e["title"].split()[:3])
    if title_ok and author_ok:
        icon = "✅"
    elif title_ok:
        icon = "🔶"
    else:
        icon = "⚠️"
    print(f"{icon} {e['key']} → {b_title[:65]}")
    print(f"     {b_author[:50] if b_author else ''} | {b_pub[:40] if b_pub else ''}")
    print(f"     BID: {b_id}")
    time.sleep(0.2)
