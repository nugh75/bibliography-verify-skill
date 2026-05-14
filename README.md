# bibliography-verify

Cross-reference bibliographic entries against:
- **OpenAlex** — academic papers, books, chapters
- **Semantic Scholar** — papers, citations  
- **OPAC SBN** — Italian library catalog (books)
- **DOAJ** — open access journals

## Prerequisites

```bash
# CLIs (install with go1.26.3 from each project dir)
# openalex-pp-cli
export OPENALEX_MAILTO="your.email@example.com"

# Python deps
pip install scholarly
```

## Usage

```bash
# Verify all entries
python3 scripts/verify_all.py

# Verify Italian books on OPAC SBN
python3 scripts/verify_opac.py
```

## CLI Manual Queries

```bash
# OpenAlex
openalex-pp-cli search --query "title keywords"

# OPAC SBN
opac-sbn-pp-cli search-json --any "author title" --rows 5 --json

# Semantic Scholar
semantic-scholar-pp-cli paper get-graph-relevance-search --query "title"
```
