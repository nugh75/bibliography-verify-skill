---
name: bibliography-verify
description: |
  Verify and enrich bibliographic references using multiple scholarly APIs:
  OpenAlex, Semantic Scholar, OPAC SBN, DOAJ, and Google Scholar (via
  scholarly). Generates a structured audit report comparing each bib entry
  against available sources. Active when the user asks to check, verify,
  validate, or audit bibliography entries.
---

# Bibliography Verify Skill `bibs`

Orchestrates multiple CLI tools to cross-reference bib entries against
scholarly databases. Detects missing entries, wrong years, author mismatches,
and suggests DOIs or stable IDs.

## Prerequisites

| Tool | Install | Auth |
|------|---------|------|
| `openalex-pp-cli` | In `openalex-pp-cli/` | `OPENALEX_MAILTO` |
| `semantic-scholar-pp-cli` | In `semantic-scholar-pp-cli/` | None (rate-limited) |
| `opac-sbn-pp-cli` | In `opac-sbn-pp-cli/` | None |
| `doaj-pp-cli` | In `doaj-pp-cli/` | None |
| `scholarly` (Python) | `pip install scholarly` | None (Captcha-prone) |
| `bib_verify_online.py` | `article-revision/scripts/bib_verify_online.py` | `OPENALEX_MAILTO` |

## Slash Commands

| Command | Action |
|---|---|
| `/bib-verify all` | Check ALL bib entries against all available sources |
| `/bib-verify openalex` | Check entries against OpenAlex only |
| `/bib-verify ss` | Check entries against Semantic Scholar only |
| `/bib-verify opac` | Check Italian books against OPAC SBN |
| `/bib-verify missing` | Check only entries not found in previous runs |
| `/bib-verify <key>` | Check a specific bib key (e.g. `/bib-verify roncaglia2020`) |

## Workflow

1. Parse `bibliography/reference.bib`
2. For each entry, query available sources in order:
   - **OpenAlex**: academic papers, books, chapters
   - **Semantic Scholar**: papers, citations
   - **OPAC SBN**: Italian library catalog (books only)
   - **Google Scholar** (via scholarly): fallback for edge cases
3. Generate an audit table comparing bib metadata vs source data
4. Flag discrepancies: year mismatch, author mismatch, wrong work
5. Suggest corrections (DOI, stable URL, BID for OPAC)

## Output Format

For each entry, report:

```
<key> | <bib_title> | <source> | score | match? | notes
```

Where the status is:
- `✅` match confirmed (title + author + year)
- `🔶` partial match (title matches, but year/author differs)
- `⚠️` low confidence (unrelated result)
- `❌` not found in any source

## Scripts

| Script | Purpose |
|---|---|
| `scripts/verify_all.py` | Check all entries against all sources |
| `scripts/verify_openalex.py` | Check against OpenAlex only |
| `scripts/verify_opac.py` | Check Italian entries against OPAC SBN |
| `scripts/update_bib.py` | Apply suggested corrections to .bib |
