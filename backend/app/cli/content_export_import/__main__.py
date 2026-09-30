from __future__ import annotations

import argparse

# Register the complete SQLAlchemy mapper graph before the CLI performs its first query.
import app.main  # noqa: F401

from .archive import ContentExportImportError, ImportAborted
from .commands import cmd_export, cmd_import


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export/import one bot's content, tests, and knowledge base",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export one bot to an archive")
    export_parser.add_argument("--bot-instance", required=True, help="Source bot slug or numeric id")
    export_parser.add_argument("--out", required=True, help="Path to write the .tar.gz archive")
    export_parser.set_defaults(func=cmd_export)

    import_parser = subparsers.add_parser(
        "import",
        help="Import an archive into an existing bot (put a live target in maintenance first)",
    )
    import_parser.add_argument("--bot-instance", required=True, help="Target bot slug or numeric id")
    import_parser.add_argument("--in", dest="archive", required=True, help="Path to the .tar.gz archive")
    import_parser.add_argument(
        "--only",
        help="Comma-separated archive parts to import: content,tests,kb",
    )
    import_parser.add_argument(
        "--commit",
        action="store_true",
        help="Persist changes; default is a full dry-run",
    )
    import_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt (the banner is still printed)",
    )
    import_parser.set_defaults(func=cmd_import)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except ImportAborted:
        print("Aborted.")
    except ContentExportImportError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
