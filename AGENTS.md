# bibliography-verify

Orchestrate bibliography verification across OpenAlex, Semantic Scholar, 
OPAC SBN, and DOAJ. Activate when the user asks to check, verify, audit, 
or cross-reference bibliography entries.

## Slash Commands

| Command | Action |
|---|---|
| `/bib-verify all` | Check ALL bib entries against all available sources |
| `/bib-verify openalex` | Check entries against OpenAlex only |
| `/bib-verify opac` | Check Italian books against OPAC SBN |

## Quick Start

```bash
cd <project-root>
python3 .claude/skills/bibliography-verify/scripts/verify_all.py
```

See `SKILL.md` for full workflow.
