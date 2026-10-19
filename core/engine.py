#!/usr/bin/env python3
"""LinkAudit core logic."""
from __future__ import annotations

from .config import load_tool_data

import argparse
import csv
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from .utils import (
    console,
    make_table,
    print_error,
    print_info,
    print_success,
    print_tool_header,
    print_warning,
    prompt_confirm,
    prompt_menu,
    prompt_text,
)

# Regex patterns for Markdown links: [text](url), ![alt](url), <https://...>, and [ref]: url
MD_INLINE_LINK_RE = re.compile(r"""!?\[[^\]]*\]\(\s*([^\s\)]+)(?:\s+['"][^'"]*['"])?\s*\)""")
MD_ANGLE_LINK_RE = re.compile(r"""<(https?://[^>\s]+)>""")
MD_REF_LINK_RE = re.compile(r"""^\s*\[[^\]]+\]:\s*(\S+)""", re.MULTILINE)

def _load_tool_data(filename: str) -> dict:
    """Thin alias: load this tool's own config via core/config.py."""
    return load_tool_data(filename)


@dataclass
class DiscoveredLink:
    target: str  # Resolved HTTP(S) URL or local file path
    raw_link: str
    source: str  # Source URL or Markdown file path
    scope: str  # internal | external | local


@dataclass
class LinkCheckResult:
    target: str
    scope: str  # internal | external | local
    status_category: str  # working | broken | redirected | timeout | blocked | inconclusive
    http_status: Optional[int] = None
    final_url: Optional[str] = None
    redirect_count: int = 0
    response_time_ms: float = 0.0
    error_message: str = ""
    sources: List[str] = field(default_factory=list)


@dataclass
class AuditReport:
    target_description: str
    total_references: int = 0
    unique_checked: int = 0
    duplicates_skipped: int = 0
    results: List[LinkCheckResult] = field(default_factory=list)

    def by_category(self, cat: str) -> List[LinkCheckResult]:
        return [r for r in self.results if r.status_category == cat]


TOOL_DATA = _load_tool_data("http_profile.json")
DEFAULT_HEADERS = {
    "User-Agent": TOOL_DATA.get("user_agent", "LinkAudit/1.0"),
    "Accept": TOOL_DATA.get("accept", "text/html,*/*"),
}
BLOCKED_STATUS_CODES = tuple(TOOL_DATA.get("blocked_status_codes", [401, 403, 429]))


def _clean_url_fragment(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, ""))


def extract_links_from_webpage(html_text: str, base_url: str) -> List[DiscoveredLink]:
    """Extract internal and external HTTP/HTTPS links from HTML content."""
    soup = BeautifulSoup(html_text, "html.parser")
    base_host = urlparse(base_url).netloc.lower()
    discovered: List[DiscoveredLink] = []

    for tag in soup.find_all(["a", "link", "img", "script"]):
        attr = "href" if tag.name in ("a", "link") else "src"
        raw = tag.get(attr)
        if not raw:
            continue
        raw_str = str(raw).strip()
        if not raw_str or raw_str.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            continue
        joined = urljoin(base_url, raw_str)
        parsed = urlparse(joined)
        if parsed.scheme not in ("http", "https"):
            continue
        clean_target = _clean_url_fragment(joined)
        scope = "internal" if parsed.netloc.lower() == base_host else "external"
        discovered.append(
            DiscoveredLink(
                target=clean_target,
                raw_link=raw_str,
                source=base_url,
                scope=scope,
            )
        )
    return discovered


def extract_links_from_markdown_text(md_text: str, source_file: Path) -> List[DiscoveredLink]:
    """Extract web URLs and relative local links from a Markdown document."""
    raw_links: List[str] = []
    for match in MD_INLINE_LINK_RE.finditer(md_text):
        raw_links.append(match.group(1))
    for match in MD_ANGLE_LINK_RE.finditer(md_text):
        raw_links.append(match.group(1))
    for match in MD_REF_LINK_RE.finditer(md_text):
        raw_links.append(match.group(1))

    discovered: List[DiscoveredLink] = []
    for raw in raw_links:
        raw_clean = raw.strip()
        if not raw_clean or raw_clean.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
            continue
        parsed = urlparse(raw_clean)
        if parsed.scheme in ("http", "https"):
            discovered.append(
                DiscoveredLink(
                    target=_clean_url_fragment(raw_clean),
                    raw_link=raw_clean,
                    source=str(source_file),
                    scope="external",
                )
            )
        elif not parsed.scheme:
            # Local relative file link in Markdown (strip #anchor)
            path_part = raw_clean.split("#", 1)[0].split("?", 1)[0]
            if not path_part:
                continue
            resolved_local = (source_file.parent / path_part).resolve()
            discovered.append(
                DiscoveredLink(
                    target=str(resolved_local),
                    raw_link=raw_clean,
                    source=str(source_file),
                    scope="local",
                )
            )
    return discovered


def check_single_link(
    target: str,
    scope: str,
    sources: Sequence[str],
    timeout: float = 10.0,
    session: Optional[requests.Session] = None,
) -> LinkCheckResult:
    """Validate an HTTP(S) URL or local file path and classify its status."""
    import time

    if scope == "local":
        p = Path(target)
        if p.exists():
            return LinkCheckResult(
                target=target,
                scope=scope,
                status_category="working",
                http_status=200,
                final_url=target,
                sources=list(sources),
            )
        return LinkCheckResult(
            target=target,
            scope=scope,
            status_category="broken",
            http_status=404,
            error_message="Local file not found",
            sources=list(sources),
        )

    sess = session or requests.Session()
    t0 = time.perf_counter()
    try:
        # Try HEAD first, fall back to GET if HEAD returns 405/403/400 or fails
        resp = sess.head(
            target,
            headers=DEFAULT_HEADERS,
            allow_redirects=True,
            timeout=timeout,
        )
        if resp.status_code in (400, 403, 405, 501) or resp.status_code >= 400:
            resp = sess.get(
                target,
                headers=DEFAULT_HEADERS,
                allow_redirects=True,
                timeout=timeout,
                stream=True,
            )
            resp.close()

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        code = resp.status_code
        redirect_cnt = len(resp.history)
        final_u = resp.url or target

        if code in BLOCKED_STATUS_CODES:
            category = "blocked"
        elif 200 <= code < 300:
            category = "redirected" if redirect_cnt > 0 else "working"
        elif 300 <= code < 400:
            category = "redirected"
        elif code >= 400:
            category = "broken"
        else:
            category = "inconclusive"

        return LinkCheckResult(
            target=target,
            scope=scope,
            status_category=category,
            http_status=code,
            final_url=final_u if redirect_cnt > 0 else None,
            redirect_count=redirect_cnt,
            response_time_ms=elapsed_ms,
            sources=list(sources),
        )
    except requests.Timeout:
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        return LinkCheckResult(
            target=target,
            scope=scope,
            status_category="timeout",
            response_time_ms=elapsed_ms,
            error_message=f"Request timed out after {timeout}s",
            sources=list(sources),
        )
    except requests.ConnectionError as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        return LinkCheckResult(
            target=target,
            scope=scope,
            status_category="broken",
            response_time_ms=elapsed_ms,
            error_message=f"Connection failed: {exc}",
            sources=list(sources),
        )
    except requests.RequestException as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
        return LinkCheckResult(
            target=target,
            scope=scope,
            status_category="inconclusive",
            response_time_ms=elapsed_ms,
            error_message=str(exc),
            sources=list(sources),
        )


def run_link_audit(
    discovered_links: Sequence[DiscoveredLink],
    target_description: str,
    check_internal: bool = True,
    check_external: bool = True,
    check_local: bool = True,
    timeout: float = 10.0,
    max_workers: int = 8,
    session: Optional[requests.Session] = None,
    show_progress: bool = True,
) -> AuditReport:
    """Filter, deduplicate, and concurrently audit discovered links."""
    filtered: List[DiscoveredLink] = []
    for lnk in discovered_links:
        if lnk.scope == "internal" and not check_internal:
            continue
        if lnk.scope == "external" and not check_external:
            continue
        if lnk.scope == "local" and not check_local:
            continue
        filtered.append(lnk)

    # Deduplicate identical target URLs while preserving all source references
    grouped: Dict[Tuple[str, str], List[str]] = {}
    for lnk in filtered:
        key = (lnk.target, lnk.scope)
        src_list = grouped.setdefault(key, [])
        if lnk.source not in src_list:
            src_list.append(lnk.source)

    report = AuditReport(
        target_description=target_description,
        total_references=len(filtered),
        unique_checked=len(grouped),
        duplicates_skipped=max(0, len(filtered) - len(grouped)),
    )

    items = list(grouped.items())
    if not items:
        return report

    sess = session or requests.Session()
    results: List[LinkCheckResult] = []

    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            task_id = progress.add_task("Auditing links...", total=len(items))
            with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
                future_map = {
                    pool.submit(check_single_link, target, scope, srcs, timeout, sess): (target, scope)
                    for (target, scope), srcs in items
                }
                for fut in as_completed(future_map):
                    results.append(fut.result())
                    progress.advance(task_id)
    else:
        with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
            futures = [
                pool.submit(check_single_link, target, scope, srcs, timeout, sess)
                for (target, scope), srcs in items
            ]
            for fut in futures:
                results.append(fut.result())

    results.sort(key=lambda r: (r.status_category, r.target))
    report.results = results
    return report


def audit_website(
    url: str,
    check_internal: bool = True,
    check_external: bool = True,
    timeout: float = 10.0,
    max_workers: int = 8,
    session: Optional[requests.Session] = None,
    show_progress: bool = True,
) -> AuditReport:
    """Scan a webpage for internal and external links and validate them."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    sess = session or requests.Session()
    resp = sess.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    resp.raise_for_status()
    base_url = resp.url or url
    discovered = extract_links_from_webpage(resp.text, base_url)
    return run_link_audit(
        discovered,
        target_description=base_url,
        check_internal=check_internal,
        check_external=check_external,
        timeout=timeout,
        max_workers=max_workers,
        session=sess,
        show_progress=show_progress,
    )


def audit_markdown_path(
    path: Path | str,
    check_external: bool = True,
    check_local: bool = True,
    timeout: float = 10.0,
    max_workers: int = 8,
    session: Optional[requests.Session] = None,
    show_progress: bool = True,
) -> AuditReport:
    """Scan a Markdown file or an entire documentation directory for broken links."""
    p = Path(path).expanduser().resolve()
    md_files: List[Path] = []
    if p.is_file():
        md_files.append(p)
    elif p.is_dir():
        md_files.extend(sorted(p.rglob("*.md")))
        md_files.extend(sorted(p.rglob("*.markdown")))
    else:
        raise FileNotFoundError(f"Path not found: {p}")

    discovered: List[DiscoveredLink] = []
    for mf in md_files:
        try:
            text = mf.read_text(encoding="utf-8", errors="replace")
            discovered.extend(extract_links_from_markdown_text(text, mf))
        except OSError:
            pass

    return run_link_audit(
        discovered,
        target_description=str(p),
        check_internal=True,
        check_external=check_external,
        check_local=check_local,
        timeout=timeout,
        max_workers=max_workers,
        session=session,
        show_progress=show_progress,
    )


def export_audit_report(report: AuditReport, output_path: Path | str, fmt: Optional[str] = None) -> Path:
    """Export LinkAudit results to JSON, CSV, or TXT."""
    out = Path(output_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    export_fmt = (fmt or out.suffix.lstrip(".") or "json").lower()

    if export_fmt == "csv":
        with open(out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "target",
                    "scope",
                    "status_category",
                    "http_status",
                    "final_url",
                    "redirect_count",
                    "response_time_ms",
                    "error_message",
                    "sources",
                ]
            )
            for r in report.results:
                writer.writerow(
                    [
                        r.target,
                        r.scope,
                        r.status_category,
                        r.http_status or "",
                        r.final_url or "",
                        r.redirect_count,
                        r.response_time_ms,
                        r.error_message,
                        "; ".join(r.sources),
                    ]
                )
    elif export_fmt == "txt":
        lines = [
            f"LinkAudit Report - {report.target_description}",
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            f"Total References: {report.total_references} | Unique Checked: {report.unique_checked} | Duplicates Skipped: {report.duplicates_skipped}",
            "=" * 80,
        ]
        for cat in ("working", "redirected", "broken", "timeout", "blocked", "inconclusive"):
            items = report.by_category(cat)
            lines.append(f"\n[{cat.upper()}] ({len(items)})")
            for item in items:
                code_str = f"HTTP {item.http_status}" if item.http_status else "NO_STATUS"
                extra = f" -> {item.final_url}" if item.final_url else ""
                if item.error_message:
                    extra += f" ({item.error_message})"
                lines.append(f"  - [{code_str}] ({item.scope}) {item.target}{extra}")
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        payload = {
            "target": report.target_description,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "summary": {
                "total_references": report.total_references,
                "unique_checked": report.unique_checked,
                "duplicates_skipped": report.duplicates_skipped,
                "working": len(report.by_category("working")),
                "redirected": len(report.by_category("redirected")),
                "broken": len(report.by_category("broken")),
                "timeout": len(report.by_category("timeout")),
                "blocked": len(report.by_category("blocked")),
                "inconclusive": len(report.by_category("inconclusive")),
            },
            "results": [asdict(r) for r in report.results],
        }
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def display_audit_report(report: AuditReport) -> None:
    color_map = {
        "working": "green",
        "redirected": "cyan",
        "broken": "bold red",
        "timeout": "yellow",
        "blocked": "magenta",
        "inconclusive": "dim white",
    }
    rows = []
    for r in report.results:
        st_color = color_map.get(r.status_category, "white")
        details = ""
        if r.final_url and r.redirect_count > 0:
            details = f"Redirects ({r.redirect_count}) -> {r.final_url}"
        elif r.error_message:
            details = r.error_message
        else:
            details = f"{r.response_time_ms:.0f} ms"
        rows.append(
            (
                f"[{st_color}]{r.status_category.upper()}[/{st_color}]",
                str(r.http_status or "-"),
                r.scope,
                r.target,
                details,
            )
        )

    console.print()
    if rows:
        console.print(
            make_table(
                title=f"LinkAudit Results - {report.target_description}",
                columns=[
                    ("Status", "bold white"),
                    ("HTTP", "cyan"),
                    ("Scope", "magenta"),
                    ("Link / Target", "white"),
                    ("Details / Destination", "dim white"),
                ],
                rows=rows,
            )
        )

    summary_rows = [
        ("Total Link References", str(report.total_references)),
        ("Unique Links Checked", str(report.unique_checked)),
        ("Duplicate Links Skipped", str(report.duplicates_skipped)),
        ("Working Links", f"[green]{len(report.by_category('working'))}[/green]"),
        ("Redirected Links", f"[cyan]{len(report.by_category('redirected'))}[/cyan]"),
        ("Broken Links", f"[bold red]{len(report.by_category('broken'))}[/bold red]"),
        ("Timed Out Links", f"[yellow]{len(report.by_category('timeout'))}[/yellow]"),
        ("Blocked (401/403/429)", f"[magenta]{len(report.by_category('blocked'))}[/magenta]"),
        ("Inconclusive", str(len(report.by_category("inconclusive")))),
    ]
    console.print(
        make_table(
            title="LinkAudit Summary",
            columns=[("Metric", "bold cyan"), ("Count", "white")],
            rows=summary_rows,
        )
    )
