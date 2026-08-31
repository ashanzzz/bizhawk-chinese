#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BizHawk Synchronization & Localization Pipeline Runner
Coordinates: Upstream Git sync -> Extraction -> AI Translation -> Source Code Patching
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT_DIR / "tools"
PATCHER_SCRIPT = TOOLS_DIR / "bizhawk_patcher.py"
TRANSLATE_SCRIPT = TOOLS_DIR / "ai_translate.py"

UPSTREAM_URL = "https://github.com/TASEmulators/BizHawk.git"


def run_command(cmd, cwd=None):
    print(f"[*] Executing: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    res = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str))
    if res.returncode != 0:
        print(f"[!] Command failed with return code {res.returncode}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="BizHawk Chinese Sync & Patch Pipeline")
    parser.add_argument("--repo-path", type=str, default=".", help="Path to BizHawk source repository")
    parser.add_argument("--sync-upstream", action="store_true", help="Fetch and merge latest code from official repository")
    parser.add_argument("--skip-ai", action="store_true", help="Skip AI translation step")
    parser.add_argument("--build", action="store_true", help="Run dotnet build after patching")
    
    args = parser.parse_args()
    repo_path = Path(args.repo_path).resolve()
    
    print("=" * 60)
    print("   BizHawk Chinese Automated Localization Pipeline")
    print("=" * 60)
    
    # 1. Sync upstream if requested
    if args.sync_upstream:
        print("\n[Step 1/4] Syncing upstream official repository...")
        # Check if upstream remote exists
        check_remote = subprocess.run(
            ["git", "remote", "get-url", "upstream"],
            cwd=repo_path, capture_output=True, text=True
        )
        if check_remote.returncode != 0:
            print(f"[*] Adding upstream remote: {UPSTREAM_URL}")
            run_command(["git", "remote", "add", "upstream", UPSTREAM_URL], cwd=repo_path)
            
        run_command(["git", "fetch", "upstream", "master"], cwd=repo_path)
        run_command(["git", "merge", "upstream/master", "--no-edit"], cwd=repo_path)
    else:
        print("\n[Step 1/4] Skipping upstream Git sync.")
        
    # 2. Extract strings
    print("\n[Step 2/4] Scanning source code and extracting UI strings...")
    run_command([sys.executable, str(PATCHER_SCRIPT), "--repo-path", str(repo_path), "--extract"])
    
    # 3. AI Translation for missing strings
    if not args.skip_ai:
        print("\n[Step 3/4] Running AI incremental translation...")
        run_command([sys.executable, str(TRANSLATE_SCRIPT)])
    else:
        print("\n[Step 3/4] Skipping AI translation.")
        
    # 4. Apply Patch
    print("\n[Step 4/4] Applying Chinese localization patch...")
    run_command([sys.executable, str(PATCHER_SCRIPT), "--repo-path", str(repo_path), "--patch"])
    
    # 5. Optional Build Verification
    if args.build:
        print("\n[Step 5/5] Building BizHawk...")
        run_command(["dotnet", "build", "-c", "Release"], cwd=repo_path)
        
    print("\n" + "=" * 60)
    print("   Localization Pipeline Completed Successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
