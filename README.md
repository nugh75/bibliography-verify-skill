# bibliography-verify

Audit BibTeX metadata against OpenAlex, Semantic Scholar, and OPAC SBN.
Each provider reports its search outcome separately.

## Install

```bash
# As a git submodule in your project
git submodule add git@github.com:nugh75/bibliography-verify-skill.git .claude/skills/bibliography-verify

# Or clone standalone
git clone git@github.com:nugh75/bibliography-verify-skill.git
```

## Usage

Run from the project root with Python 3.9 or newer. Set `OPENALEX_API_KEY`
in the environment if you have an OpenAlex key. See
[OpenAlex authentication](https://help.openalex.org/api/authentication/).

```bash
python3 .claude/skills/bibliography-verify/scripts/verify_all.py
python3 .claude/skills/bibliography-verify/scripts/verify_all.py --source openalex --key my-citation
python3 .claude/skills/bibliography-verify/scripts/verify_all.py --source opac-sbn --bib other.bib
```

See [SKILL.md](SKILL.md) for all modes and the report statuses.
