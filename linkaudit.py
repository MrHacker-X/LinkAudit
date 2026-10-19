#!/usr/bin/env python3
"""
LinkAudit - Broken Link Checker.

Author  : MrHacker-X
Repo    : https://github.com/MrHacker-X/linkaudit
Version : 1.0.0
"""
from __future__ import annotations

import argparse
import sys

from core.config import load_defaults
from core.engine import *  # noqa: F401,F403
from core.utils import *  # noqa: F401,F403

_defaults = load_defaults()
__version__ = str(_defaults.get("version", "1.0.0"))
TOOL_DESC = str(_defaults.get("description", "Website URL, Markdown file path, or local documentation directory"))
TOOL_NAME = str(_defaults.get("name", "LinkAudit"))


def register_subparser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "target",
        nargs="?",
        help="Website URL, Markdown file path, or local documentation directory",
    )
    parser.add_argument(
        "--internal-only",
        action="store_true",
        help="Check only internal website links",
    )
    parser.add_argument(
        "--external-only",
        action="store_true",
        help="Check only external HTTP/HTTPS links",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP request timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=8,
        help="Concurrent worker threads (default: 8)",
    )
    parser.add_argument(
        "-e",
        "--export",
        help="Export detailed report to JSON, CSV, or TXT file path",
    )
    parser.set_defaults(func=run_cli)


def run_cli(args: argparse.Namespace) -> int:
    if not getattr(args, "target", None):
        run_interactive()
        return 0

    print_tool_header("LinkAudit", "Broken Link Checker", icon="🔗")
    target = str(args.target).strip()
    check_internal = not args.external_only
    check_external = not args.internal_only

    try:
        local_candidate = Path(target).expanduser()
        if local_candidate.exists():
            report = audit_markdown_path(
                local_candidate,
                check_external=check_external,
                check_local=check_internal,
                timeout=args.timeout,
                max_workers=args.workers,
            )
        else:
            report = audit_website(
                target,
                check_internal=check_internal,
                check_external=check_external,
                timeout=args.timeout,
                max_workers=args.workers,
            )
        display_audit_report(report)
        if args.export:
            saved = export_audit_report(report, args.export)
            print_success(f"Detailed LinkAudit report saved to {saved}")
        return 0
    except Exception as exc:
        print_error(f"LinkAudit failed: {exc}")
        return 1


def run_interactive() -> None:
    print_tool_header("LinkAudit", "Broken Link Checker", icon="🔗")
    while True:
        choice = prompt_menu(
            "Menu",
            [
                ("1", "Scan all links"),
                ("2", "Internal links only"),
                ("3", "External links only"),
                ("4", "Scan Markdown file"),
                ("5", "Scan docs directory"),
                ("a", "About"),
            ],
        )
        if choice == "0":
            return
        if choice == "a":
            show_about_panel()
            console.input("[dim]Press Enter to return to the menu...[/dim]")
            continue

        try:
            if choice in ("1", "2", "3"):
                url = prompt_text("Enter website URL to scan")
                timeout_str = prompt_text("Request timeout in seconds", default="10")
                timeout_val = float(timeout_str) if timeout_str else 10.0
                rep = audit_website(
                    url,
                    check_internal=(choice in ("1", "2")),
                    check_external=(choice in ("1", "3")),
                    timeout=timeout_val,
                )
            else:
                path_str = prompt_text("Enter Markdown file or documentation directory path")
                rep = audit_markdown_path(path_str)

            display_audit_report(rep)
            if prompt_confirm("Export detailed report to file (JSON / CSV / TXT)?", default=False):
                out_path = prompt_text("Export path (e.g. link_report.json, link_report.csv, link_report.txt)", default="link_report.json")
                saved = export_audit_report(rep, out_path)
                print_success(f"Saved report to {saved}")
        except Exception as exc:
            print_error(f"LinkAudit error: {exc}")



# ----------------------------------------------------------------------------
# CLI main
# ----------------------------------------------------------------------------



def build_arg_parser() -> argparse.ArgumentParser:
    """Build the standalone CLI parser for linkaudit."""
    parser = argparse.ArgumentParser(
        prog="linkaudit",
        description=TOOL_DESC,
        epilog=(
            "GitHub: https://github.com/MrHacker-X/linkaudit - "
            "Run without flags to launch the interactive terminal menu."
        ),
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=TOOL_NAME + " " + __version__,
    )
    parser.add_argument(
        "-a",
        "--about",
        action="store_true",
        help="Show the About screen - overview, key features, version, author and contacts - and exit",
    )
    register_subparser(parser)
    return parser


def main(argv=None) -> int:
    """Entry point: parse flags and dispatch, or launch the interactive menu."""
    try:
        if argv is None:
            argv = sys.argv[1:]
        if not argv:
            # Plain `python linkaudit.py` opens the interactive terminal menu.
            run_interactive()
            return 0
        parser = build_arg_parser()
        args = parser.parse_args(argv)
        if getattr(args, "about", False):
            show_about_panel()
            return 0
        func = getattr(args, "func", run_cli)
        result = func(args)
        return int(result) if isinstance(result, (int, float)) else 0
    except (KeyboardInterrupt, EOFError):
        return handle_keyboard_interrupt()


if __name__ == "__main__":
    raise SystemExit(main())
