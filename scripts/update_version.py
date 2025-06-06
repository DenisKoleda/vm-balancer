#!/usr/bin/env python3
"""
Script to update version in all relevant files
"""

import argparse
import re
import sys
from pathlib import Path


def update_version_in_file(
    file_path: Path, version: str, pattern: str, replacement: str
):
    """Update version in a specific file using regex pattern"""
    try:
        content = file_path.read_text(encoding="utf-8")
        new_content = re.sub(pattern, replacement.format(version=version), content)

        if content != new_content:
            file_path.write_text(new_content, encoding="utf-8")
            print(f"✅ Updated {file_path}")
            return True
        else:
            print(f"⚠️  No changes in {file_path}")
            return False
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Update version in project files")
    parser.add_argument("version", help="New version (e.g., 2.0.1)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )

    args = parser.parse_args()
    version = args.version

    # Validate version format
    if not re.match(r"^\d+\.\d+\.\d+(-\w+)?$", version):
        print(
            "❌ Invalid version format. Use semantic versioning (e.g., 2.0.1 or"
            " 2.0.1-beta)"
        )
        sys.exit(1)

    project_root = Path(__file__).parent

    # Files to update
    files_to_update = [
        {
            "file": project_root / "setup.py",
            "pattern": r'version="[^"]*"',
            "replacement": 'version="{version}"',
        },
        {
            "file": project_root / "pyproject.toml",
            "pattern": r'version = "[^"]*"',
            "replacement": 'version = "{version}"',
        },
        {
            "file": project_root / "src" / "vm_balancer" / "__init__.py",
            "pattern": r'__version__ = "[^"]*"',
            "replacement": '__version__ = "{version}"',
        },
    ]

    if args.dry_run:
        print(f"🔍 Dry run: Would update version to {version} in:")
        for file_info in files_to_update:
            if file_info["file"].exists():
                print(f"  - {file_info['file']}")
            else:
                print(f"  - {file_info['file']} (file not found)")
        return

    print(f"🚀 Updating version to {version}...")

    updated_files = 0
    for file_info in files_to_update:
        if file_info["file"].exists():
            if update_version_in_file(
                file_info["file"],
                version,
                file_info["pattern"],
                file_info["replacement"],
            ):
                updated_files += 1
        else:
            print(f"⚠️  File not found: {file_info['file']}")

    print(f"\n✅ Updated {updated_files} files")

    # Instructions for next steps
    print(f"""
📋 Next steps:
1. Review the changes: git diff
2. Commit the changes: git add . && git commit -m "Bump version to {version}"
3. Create a tag: git tag -a v{version} -m "Release v{version}"
4. Push changes: git push && git push --tags
5. Or use GitHub Actions manual workflow to publish
""")


if __name__ == "__main__":
    main()
