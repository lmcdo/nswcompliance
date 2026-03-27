"""
Enrichment Pipeline for Provision-Based Architecture

This module enriches regulatory provisions with metadata to support
automatic filtering via Planning Portal data.

Phases:
1. Numeric extraction (regex-based, free)
2. Type classification (batch LLM)
3. Site condition tagging (keyword-based)
4. Applicability tagging (rules + LLM)
"""

__version__ = "1.0.0"
