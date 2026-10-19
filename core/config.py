#!/usr/bin/env python3
"""LinkAudit configuration constants (built-in, self-contained)."""
from __future__ import annotations

_CONFIGS: dict = {
    "defaults.json": {
        "tool": "linkaudit",
        "name": "LinkAudit",
        "subtitle": "Broken Link Checker",
        "version": "1.1.0",
        "description": "Website URL, Markdown file path, or local documentation directory",
        "homepage": "https://github.com/MrHacker-X/linkaudit",
        "author": "MrHacker-X",
        "email": "contact@vritrasec.com",
        "website": "https://vritrasec.com",
        "network": "https://link.vritrasec.com",
        "about_overview": (
            "LinkAudit is a thorough broken-link checker: feed it a URL, a Markdown file or a whole documentation directory and it extracts every link, verifies each one with concurrent HTTP checks, and reports exactly which links are broken - with exportable JSON/CSV/TXT reports for CI."
        ),
        "about_features": [
            "Audits websites, Markdown files and doc directories",
            "Concurrent link verification with worker threads",
            "Internal-only / external-only scan modes",
            "Detailed JSON, CSV and TXT report export",
            "Clear broken-link reporting for docs and CI pipelines",
            "Dual interface: interactive menu or direct CLI flags",
        ]
    },
    "http_profile.json": {
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 LinkAudit/1.0",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "default_timeout": 10.0,
        "default_workers": 8,
        "blocked_status_codes": [
            401,
            403,
            429
        ],
        "http_fallback_head_codes": [
            400,
            403,
            405,
            501
        ]
    }
}


def load_tool_data(filename: str) -> dict:
    """Return the built-in configuration table stored under `filename`."""
    return dict(_CONFIGS.get(filename, {}))


def load_defaults() -> dict:
    """Return the tool identity / defaults configuration."""
    return dict(_CONFIGS.get("defaults.json", {}))
