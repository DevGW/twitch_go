#!/usr/bin/env python3
"""
Release script for twitch-go.

Builds the executable with PyInstaller, creates release archives, and optionally
creates a GitHub release.

Usage:
    python release.py [--no-tag] [--no-release] [--version X.Y.Z]
"""

import subprocess
import sys
import shutil
import tomllib
from pathlib import Path
from datetime import datetime

# Try to import tomllib (Python 3.11+) or use tomli as fallback
try:
    import tomllib
    TOML_LOAD_MODE = "rb"
except ImportError:
    try:
        import tomli as tomllib
        TOML_LOAD_MODE = "rb"
    except ImportError:
        print("ERROR: Need Python 3.11+ or install tomli: pip install tomli")
        sys.exit(1)

PROJECT_ROOT = Path(__file__).parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
RELEASE_DIR = PROJECT_ROOT / "releases"

def get_version(version_override=None):
    """Get version from pyproject.toml or use override."""
    if version_override:
        return version_override
    
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    with open(pyproject_path, TOML_LOAD_MODE) as f:
        data = tomllib.load(f)
    return data["project"]["version"]

def clean_builds():
    """Clean previous build artifacts."""
    print("Cleaning previous builds...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    print("✓ Cleaned build directories")

def build_executable():
    """Build executable with PyInstaller."""
    print("\nBuilding executable with PyInstaller...")
    result = subprocess.run(
        [
            "pyinstaller",
            "--onefile",
            "--name", "twitch-go",
            "twitch_go_cli.py"
        ],
        cwd=PROJECT_ROOT,
        check=True
    )
    print("✓ Build complete")

def create_release_archive(version):
    """Create release archive from built executable."""
    print(f"\nCreating release archive for v{version}...")
    
    RELEASE_DIR.mkdir(exist_ok=True)
    
    # Find the built executable
    if sys.platform == "win32":
        exe_name = "twitch-go.exe"
        archive_name = f"twitch-go-v{version}-windows.zip"
        archive_path = RELEASE_DIR / archive_name
        
        import zipfile
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(DIST_DIR / exe_name, exe_name)
    else:
        exe_name = "twitch-go"
        archive_name = f"twitch-go-v{version}-{sys.platform}.tar.gz"
        archive_path = RELEASE_DIR / archive_name
        
        import tarfile
        with tarfile.open(archive_path, "w:gz") as tf:
            tf.add(DIST_DIR / exe_name, arcname=exe_name)
    
    print(f"✓ Created {archive_name}")
    return archive_path

def check_git_repo():
    """Check if we're in a git repository with commits."""
    try:
        # Check if git repo exists
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            check=True
        )
        # Check if HEAD exists (has commits)
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def create_git_tag(version):
    """Create and push git tag."""
    if not check_git_repo():
        print("⚠️  Not in a git repository or no commits found. Skipping tag creation.")
        return False
    
    print(f"\nCreating git tag v{version}...")
    
    # Check if tag already exists
    result = subprocess.run(
        ["git", "tag", "-l", f"v{version}"],
        capture_output=True,
        text=True
    )
    if result.stdout.strip():
        response = input(f"Tag v{version} already exists. Overwrite? [y/N]: ")
        if response.lower() != "y":
            print("Skipping tag creation")
            return False
        subprocess.run(["git", "tag", "-d", f"v{version}"], check=False)
    
    # Create tag
    try:
        subprocess.run(["git", "tag", "-a", f"v{version}", "-m", f"Release v{version}"], check=True)
        print(f"✓ Created tag v{version}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Failed to create tag: {e}")
        return False
    
    # Ask to push
    response = input("Push tag to remote? [y/N]: ")
    if response.lower() == "y":
        try:
            subprocess.run(["git", "push", "origin", f"v{version}"], check=True)
            print("✓ Pushed tag to remote")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to push tag: {e}")
            return False
    
    return True

def create_github_release(version, archive_path):
    """Create GitHub release using gh CLI."""
    print(f"\nCreating GitHub release v{version}...")
    
    # Check if gh CLI is available
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: GitHub CLI (gh) not found. Install from https://cli.github.com/")
        print("Or manually create release at https://github.com/DevGW/twitch_go/releases/new")
        return False
    
    # Check if already logged in
    try:
        subprocess.run(["gh", "auth", "status"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("ERROR: Not authenticated with GitHub CLI. Run: gh auth login")
        return False
    
    # Check if release already exists for this tag
    try:
        result = subprocess.run(
            ["gh", "release", "view", f"v{version}"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            # Release exists, ask to upload asset
            response = input(f"Release v{version} already exists. Upload asset to existing release? [y/N]: ")
            if response.lower() != "y":
                print("Skipping release update")
                return False
            # Upload asset to existing release
            try:
                subprocess.run(
                    ["gh", "release", "upload", f"v{version}", str(archive_path), "--clobber"],
                    check=True
                )
                print(f"✓ Uploaded {archive_path.name} to existing release v{version}")
                return True
            except subprocess.CalledProcessError as e:
                print(f"ERROR: Failed to upload asset: {e}")
                return False
    except FileNotFoundError:
        pass  # gh command failed, continue to create new release
    
    # Create new release
    release_notes = f"""# Release v{version}

Built on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Installation

Download the archive for your platform and extract the executable.

## Changes

[Add release notes here]
"""
    
    try:
        subprocess.run(
            [
                "gh", "release", "create",
                f"v{version}",
                str(archive_path),
                "--title", f"Release v{version}",
                "--notes", release_notes
            ],
            check=True
        )
        print(f"✓ Created GitHub release v{version}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to create release: {e}")
        print(f"Error details: {e.stderr if hasattr(e, 'stderr') else 'Unknown error'}")
        return False

def bump_version(current_version, bump_type):
    """Bump version number."""
    parts = current_version.split(".")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    
    return f"{major}.{minor}.{patch}"

def update_pyproject_version(version):
    """Update version in pyproject.toml."""
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    
    # Read current file
    with open(pyproject_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Update version (simple string replacement)
    import re
    content = re.sub(
        r'version = "[^"]+"',
        f'version = "{version}"',
        content
    )
    
    # Write back
    with open(pyproject_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✓ Updated pyproject.toml to v{version}")

def interactive_version_selection(current_version):
    """Interactively select or enter version."""
    print(f"\nCurrent version: v{current_version}")
    print("\nVersion options:")
    print("  1. Keep current version")
    print("  2. Bump patch (0.1.0 → 0.1.1)")
    print("  3. Bump minor (0.1.0 → 0.2.0)")
    print("  4. Bump major (0.1.0 → 1.0.0)")
    print("  5. Enter custom version")
    
    choice = input("\nSelect option [1-5] (default: 1): ").strip() or "1"
    
    if choice == "1":
        return current_version
    elif choice == "2":
        new_version = bump_version(current_version, "patch")
    elif choice == "3":
        new_version = bump_version(current_version, "minor")
    elif choice == "4":
        new_version = bump_version(current_version, "major")
    elif choice == "5":
        new_version = input("Enter version (e.g., 1.2.3): ").strip()
        if not new_version:
            print("Invalid version, keeping current")
            return current_version
    else:
        print("Invalid choice, keeping current version")
        return current_version
    
    # Confirm version change
    if new_version != current_version:
        confirm = input(f"\nUpdate version to v{new_version}? [y/N]: ")
        if confirm.lower() == "y":
            update_pyproject_version(new_version)
            return new_version
    
    return current_version

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build and release twitch-go")
    parser.add_argument("--version", help="Version override (default: from pyproject.toml)")
    parser.add_argument("--no-tag", action="store_true", help="Skip git tag creation")
    parser.add_argument("--no-release", action="store_true", help="Skip GitHub release")
    parser.add_argument("--no-archive", action="store_true", help="Skip archive creation")
    parser.add_argument("--non-interactive", action="store_true", help="Skip interactive prompts")
    args = parser.parse_args()
    
    # Get initial version
    initial_version = get_version(args.version)
    
    # Interactive version selection (unless version override or non-interactive)
    if args.version:
        version = args.version
    elif args.non_interactive:
        version = initial_version
    else:
        version = interactive_version_selection(initial_version)
    
    print(f"\n{'='*60}")
    print(f"Building release v{version}")
    print(f"{'='*60}\n")
    
    # Confirm before proceeding (unless non-interactive)
    if not args.non_interactive:
        print("This will:")
        print("  1. Clean previous builds")
        print("  2. Build executable with PyInstaller")
        if not args.no_archive:
            print("  3. Create release archive")
        if not args.no_tag:
            print("  4. Create git tag (if in git repo)")
        if not args.no_release:
            print("  5. Create GitHub release (if gh CLI available)")
        
        confirm = input("\nProceed? [y/N]: ")
        if confirm.lower() != "y":
            print("Aborted")
            return
    
    # Build steps
    clean_builds()
    build_executable()
    
    if not args.no_archive:
        archive_path = create_release_archive(version)
    else:
        archive_path = None
    
    if not args.no_tag:
        if not args.non_interactive:
            tag_confirm = input("\nCreate git tag? [Y/n]: ").strip().lower()
            if tag_confirm != "n":
                create_git_tag(version)
        else:
            create_git_tag(version)
    
    if not args.no_release and archive_path:
        if not args.non_interactive:
            release_confirm = input("\nCreate GitHub release? [Y/n]: ").strip().lower()
            if release_confirm != "n":
                create_github_release(version, archive_path)
        else:
            create_github_release(version, archive_path)
    
    print(f"\n{'='*60}")
    print(f"✓ Release v{version} complete!")
    if archive_path:
        print(f"  Archive: {archive_path}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

