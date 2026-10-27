#!/usr/bin/env python3
"""
💖 Waifu on Telegram - Release Automation Script
Usage:
    python scripts/release.py 1.1.0
"""

import os
import sys
import re
import json
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Terminal Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

def c(color, text):
    return f"{color}{text}{RESET}"

def get_current_version() -> str:
    v_file = os.path.join(PROJECT_ROOT, "VERSION")
    if os.path.exists(v_file):
        with open(v_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "1.0.0"

def update_version_files(new_ver: str):
    # 1. Update VERSION file
    v_file = os.path.join(PROJECT_ROOT, "VERSION")
    with open(v_file, "w", encoding="utf-8") as f:
        f.write(new_ver + "\n")
    print(c(GREEN, f"  ✓ Updated VERSION -> {new_ver}"))

    # 2. Update package.json
    pkg_file = os.path.join(PROJECT_ROOT, "package.json")
    if os.path.exists(pkg_file):
        with open(pkg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["version"] = new_ver
        with open(pkg_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(c(GREEN, f"  ✓ Updated package.json -> {new_ver}"))

    # 3. Update package-lock.json
    lock_file = os.path.join(PROJECT_ROOT, "package-lock.json")
    if os.path.exists(lock_file):
        with open(lock_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["version"] = new_ver
        if "packages" in data and "" in data["packages"]:
            data["packages"][""]["version"] = new_ver
        with open(lock_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(c(GREEN, f"  ✓ Updated package-lock.json -> {new_ver}"))

def main():
    if len(sys.argv) < 2:
        cur = get_current_version()
        print(c(BOLD + MAGENTA, f"Current Version: v{cur}"))
        print(c(YELLOW, "Usage: python scripts/release.py <version> (e.g. 1.1.0)"))
        sys.exit(1)

    raw_ver = sys.argv[1].strip().lstrip("v")
    if not re.match(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$", raw_ver):
        print(c(RED, f"Error: Invalid semantic version format '{raw_ver}'. Expected format: X.Y.Z (e.g. 1.1.0)"))
        sys.exit(1)

    tag_name = f"v{raw_ver}"
    print(c(BOLD + CYAN, f"\n🚀 Preparing Release {tag_name}...\n"))

    # Update files
    update_version_files(raw_ver)

    # Git commit & tag
    try:
        subprocess.run(["git", "add", "VERSION", "package.json", "package-lock.json"], cwd=PROJECT_ROOT, check=True)
        
        # Check if there are staged changes
        status = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=PROJECT_ROOT)
        if status.returncode != 0:
            commit_msg = f"chore: release {tag_name}"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=PROJECT_ROOT, check=True)
            print(c(GREEN, f"  ✓ Created git commit: '{commit_msg}'"))
        
        # Create tag
        subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"], cwd=PROJECT_ROOT, check=True)
        print(c(GREEN, f"  ✓ Created git tag: {tag_name}"))

        # Push to remote
        print(c(CYAN, f"\nPushing {tag_name} and commits to GitHub origin/main..."))
        subprocess.run(["git", "push", "origin", "main"], cwd=PROJECT_ROOT, check=True)
        subprocess.run(["git", "push", "origin", tag_name], cwd=PROJECT_ROOT, check=True)
        print(c(BOLD + GREEN, f"\n🎉 Release {tag_name} published successfully!"))
        print(c(CYAN, "GitHub Actions is now automatically building and publishing the official release on GitHub!"))

    except subprocess.CalledProcessError as e:
        print(c(RED, f"Git error occurred: {e}"))
        sys.exit(1)

if __name__ == "__main__":
    main()
