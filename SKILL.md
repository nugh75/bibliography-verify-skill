---
name: bibliography-verify
description: Audit BibTeX titles, authors, years, and identifiers against OpenAlex, Semantic Scholar, and OPAC SBN. Use when the user requests verification of existing bibliography entries.
---

# Bibliography Verify

Run `scripts/verify_all.py` from the project root with Python 3.9 or newer.
It reads `bibliography/reference.bib` by default. Override the path with
`--bib` or `BIBLIOGRAPHY_BIB_PATH`.

| Request | Arguments |
|---|---|
| `/bib-verify all` | `--source all` |
| `/bib-verify openalex` | `--source openalex` |
| `/bib-verify ss` | `--source semantic-scholar` |
| `/bib-verify opac` | `--source opac-sbn` |
| `/bib-verify <key>` | `--key <key>` |

OpenAlex accepts an optional `OPENALEX_API_KEY` in the environment.
See [OpenAlex authentication](https://help.openalex.org/api/authentication/).
OPAC SBN is queried for books, contributions to collected volumes, reports,
and miscellaneous entries.

For each key, report the status of each source:

- `high`, `medium`, `low` give the confidence of a candidate match.
  Compare title, author and year and inspect the supplied identifier before
  proposing a correction.
- `not_found` means the query succeeded with no candidate.
- `not_queried` means the source was outside the selected scope or the
  entry lacked a title.
- `error` means the request failed or the response was unusable.

Report bibliographic corrections for review. Apply approved corrections to
the named BibTeX file and re-run the audit for the affected keys.
