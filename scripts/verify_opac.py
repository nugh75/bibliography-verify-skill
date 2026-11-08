#!/usr/bin/env python3
"""Verify Italian BibTeX entries against OPAC SBN."""

from verify_all import main


if __name__ == "__main__":
    main(default_source="opac-sbn")
