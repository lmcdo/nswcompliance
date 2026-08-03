# prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md)
"""Command-line entry point.

Exit codes:
    0  clean — no flagged language in scanned lines
    1  findings — flagged language present
    2  usage or configuration error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import Config, ConfigError, builtin_presets, load_config, resolve_terms
from .diff import GitError, added_since, added_staged
from .render import RENDERERS
from .scanner import scan
from .selectors import is_user_facing
from .terms import compile_terms


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prose-gate",
        description=(
            "Diff-aware linter for risky assurance language in user-facing "
            "text. By default, scans lines added since the configured base "
            "branch."
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--diff-base",
        metavar="REF",
        help="scan lines added since merge-base(REF, HEAD) (default mode)",
    )
    mode.add_argument(
        "--staged",
        action="store_true",
        help="scan lines currently staged for commit",
    )
    mode.add_argument(
        "--full",
        nargs="+",
        metavar="FILE",
        help="scan whole files (audit mode; ignores user_facing patterns)",
    )
    parser.add_argument("--config", metavar="PATH", help="path to .prose-gate.toml")
    parser.add_argument(
        "--preset",
        metavar="NAME",
        help="bundled preset name or path to a custom preset TOML",
    )
    parser.add_argument(
        "--format",
        choices=sorted(RENDERERS),
        default="text",
        help="output format (default: text)",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="list bundled presets and exit",
    )
    return parser


def _read_full_files(paths: list[str]) -> dict[str, list[tuple[int, str]]]:
    files: dict[str, list[tuple[int, str]]] = {}
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file():
            raise ConfigError(f"file not found: {raw_path}")
        text = path.read_text(encoding="utf-8", errors="replace")
        files[raw_path] = list(enumerate(text.splitlines(), start=1))
    return files


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.list_presets:
        print("\n".join(sorted(builtin_presets())))
        return 0

    try:
        cfg: Config = load_config(args.config)
        if args.preset:
            cfg.preset = args.preset
        if args.diff_base:
            cfg.diff_base = args.diff_base
        pattern = compile_terms(resolve_terms(cfg))

        if args.full:
            files = _read_full_files(args.full)
        elif args.staged:
            files = added_staged()
        else:
            files = added_since(cfg.diff_base)

        if not args.full:
            files = {
                path: lines
                for path, lines in files.items()
                if is_user_facing(path, cfg.user_facing)
            }
    except ConfigError as exc:
        print(f"prose-gate: {exc}", file=sys.stderr)
        return 2
    except GitError as exc:
        print(f"prose-gate: git error: {exc}", file=sys.stderr)
        return 2

    findings = scan(files, pattern, cfg.exclusions)
    output = RENDERERS[args.format](findings)
    if output:
        print(output)
    return 1 if findings else 0


def entry() -> None:
    sys.exit(main())


if __name__ == "__main__":
    entry()
