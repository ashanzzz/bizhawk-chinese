#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Release Packaging Tool for BizHawk-Chinese
Safely overlays compiled binaries into the official release package and generates BizHawk-Chinese-Win-x64.zip
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def assemble_release():
    release_zip_name = "official_release.zip"
    dest_folder = ROOT_DIR / "BizHawk-Chinese"
    output_zip = ROOT_DIR / "BizHawk-Chinese-Win-x64.zip"
    build_output = ROOT_DIR / "bizhawk_src" / "output"
    
    dest_folder.mkdir(parents=True, exist_ok=True)
    
    # 1. Extract official release if present
    if os.path.exists(release_zip_name):
        print(f"[*] Extracting {release_zip_name} to {dest_folder}...")
        with zipfile.ZipFile(release_zip_name, 'r') as zip_ref:
            zip_ref.extractall(dest_folder)
            
    # Check if files were extracted inside a subfolder
    subdirs = [d for d in dest_folder.iterdir() if d.is_dir()]
    if len(subdirs) == 1 and not (dest_folder / "EmuHawk.exe").exists() and (subdirs[0] / "EmuHawk.exe").exists():
        print(f"[*] Flattening nested subfolder: {subdirs[0].name}")
        for item in subdirs[0].iterdir():
            shutil.move(str(item), str(dest_folder))
        shutil.rmtree(subdirs[0])
        
    # 2. Overlay translated compiled binaries
    if build_output.exists():
        print(f"[*] Overlaying translated binaries from {build_output} to {dest_folder}...")
        for root, dirs, files in os.walk(build_output):
            rel_dir = Path(root).relative_to(build_output)
            target_sub = dest_folder / rel_dir
            target_sub.mkdir(parents=True, exist_ok=True)
            for f in files:
                src_file = Path(root) / f
                dst_file = target_sub / f
                shutil.copy2(src_file, dst_file)
                
    # 3. Create Release ZIP Archive
    print(f"[*] Creating final distribution archive: {output_zip}...")
    if output_zip.exists():
        output_zip.unlink()
        
    shutil.make_archive(
        base_name=str(output_zip.with_suffix("")),
        format="zip",
        root_dir=str(dest_folder)
    )
    
    print(f"[+] Release package assembled successfully: {output_zip} (size: {output_zip.stat().st_size / (1024*1024):.2f} MB)")


if __name__ == "__main__":
    assemble_release()
