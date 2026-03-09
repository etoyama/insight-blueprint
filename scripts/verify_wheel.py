"""Verify that a built wheel contains required files.

Checks:
- insight_blueprint/static/index.html exists
- At least one .js file under insight_blueprint/static/assets/
- insight_blueprint/py.typed exists (PEP 561)

Usage:
    python scripts/verify_wheel.py [--dist-dir dist/]
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path


def verify_wheel(whl_path: Path) -> tuple[bool, list[str]]:
    """Verify that a wheel file contains all required files.

    Args:
        whl_path: Path to the .whl file.

    Returns:
        A tuple of (success, messages) where success is True if all checks pass.
    """
    messages: list[str] = []
    errors: list[str] = []

    with zipfile.ZipFile(whl_path) as zf:
        names = zf.namelist()

        # Check index.html
        has_html = any("static/index.html" in n for n in names)
        if has_html:
            messages.append("OK: insight_blueprint/static/index.html found")
        else:
            errors.append("ERROR: insight_blueprint/static/index.html not found")

        # Check JS assets
        has_js = any("static/assets/" in n and n.endswith(".js") for n in names)
        if has_js:
            js_files = [n for n in names if "static/assets/" in n and n.endswith(".js")]
            messages.append(f"OK: {len(js_files)} .js file(s) found in static/assets/")
        else:
            errors.append(
                "ERROR: No .js files found under insight_blueprint/static/assets/"
            )

        # Check py.typed
        has_py_typed = any(n.endswith("py.typed") for n in names)
        if has_py_typed:
            messages.append("OK: insight_blueprint/py.typed found")
        else:
            errors.append("ERROR: insight_blueprint/py.typed not found")

        # Summary
        static_count = sum(1 for n in names if "static/" in n)
        messages.append(f"Total static files in wheel: {static_count}")

    all_messages = errors + messages
    return len(errors) == 0, all_messages


def main() -> None:
    """CLI entry point for wheel verification."""
    parser = argparse.ArgumentParser(description="Verify wheel contents")
    parser.add_argument(
        "--dist-dir",
        default="dist/",
        help="Directory containing .whl files (default: dist/)",
    )
    args = parser.parse_args()

    dist_dir = Path(args.dist_dir)
    wheels = list(dist_dir.glob("*.whl"))

    if not wheels:
        print(f"ERROR: No .whl files found in {dist_dir}")
        sys.exit(1)

    whl_path = wheels[0]
    print(f"Verifying: {whl_path.name}")

    ok, messages = verify_wheel(whl_path)
    for msg in messages:
        print(f"  {msg}")

    if ok:
        print("Wheel verification PASSED")
        sys.exit(0)
    else:
        print("Wheel verification FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
