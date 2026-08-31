#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BizHawk Patcher & Extraction Engine
Extracts UI strings from BizHawk C# source code and safely applies Chinese localization patches.
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
LOCALE_DIR = ROOT_DIR / "locale"
RULES_FILE = LOCALE_DIR / "rules.json"
ZH_CN_FILE = LOCALE_DIR / "zh_CN.json"
AUTO_GEN_FILE = LOCALE_DIR / "auto_generated.json"


def load_json(filepath: Path) -> dict:
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath: Path, data: dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_flattened_dict() -> Dict[str, str]:
    """Loads and flattens all dictionary sections into a single key->translation map."""
    zh_dict = load_json(ZH_CN_FILE)
    auto_dict = load_json(AUTO_GEN_FILE)
    
    flat_map = {}
    
    # Load auto-generated dictionary first (lower priority)
    for k, v in auto_dict.items():
        if isinstance(v, str) and v.strip():
            flat_map[k] = v
            
    # Load manual zh_CN dictionary (higher priority)
    for section_name, section_content in zh_dict.items():
        if isinstance(section_content, dict):
            for k, v in section_content.items():
                if isinstance(v, str) and v.strip():
                    flat_map[k] = v
        elif isinstance(section_content, str):
            flat_map[section_name] = section_content
            
    return flat_map


def is_blacklisted(text: str, rules: dict) -> bool:
    """Checks if a string is blacklisted or code/data literal."""
    if not text or len(text.strip()) == 0:
        return True
        
    text_clean = text.strip()
    
    # Check exact blacklist
    if text_clean in rules.get("blacklist_exact", []):
        return True
        
    # Check regex blacklist
    for pattern in rules.get("blacklist_regex", []):
        if re.search(pattern, text_clean):
            return True
            
    # Check single character or purely numbers/symbols
    if len(text_clean) <= 1 and not ('\u4e00' <= text_clean <= '\u9fff'):
        return True
        
    return False


def scan_source_files(repo_path: Path, rules: dict) -> List[Path]:
    """Scans and finds all candidate C# files based on rules."""
    scan_dirs = rules.get("scan_directories", ["src/BizHawk.Client.EmuHawk", "src/BizHawk.Client.Common", "src/BizHawk.WinForms.Controls"])
    exclude_dirs = set(rules.get("exclude_directories", []))
    extensions = set(rules.get("file_extensions", [".cs"]))
    
    matched_files = []
    
    for rel_scan_dir in scan_dirs:
        target_dir = repo_path / rel_scan_dir
        if not target_dir.exists():
            continue
            
        for root, dirs, files in os.walk(target_dir):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in extensions:
                    matched_files.append(Path(root) / file)
                    
    return matched_files


def extract_strings(repo_path: Path) -> Tuple[Set[str], Set[str]]:
    """
    Extracts all candidate UI strings from BizHawk source files.
    Returns (all_found_strings, missing_strings)
    """
    rules = load_json(RULES_FILE)
    dict_map = get_flattened_dict()
    files = scan_source_files(repo_path, rules)
    
    all_strings: Set[str] = set()
    missing_strings: Set[str] = set()
    
    patterns = [re.compile(p["regex"]) for p in rules.get("match_patterns", [])]
    
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            print(f"[Warning] Failed to read {file_path}: {e}")
            continue
            
        for pattern in patterns:
            for match in pattern.finditer(content):
                # match group 2 is the text between delimiters
                text = match.group(2) if match.lastindex and match.lastindex >= 2 else match.group(0)
                if text and not is_blacklisted(text, rules):
                    all_strings.add(text)
                    if text not in dict_map:
                        missing_strings.add(text)
                        
    return all_strings, missing_strings


def apply_custom_hardcoded_patches(repo_path: Path):
    """Applies specific code-level patches for interpolated strings, dialogs, and errors."""
    print("[*] Applying specialized UI and dialog patches...")
    
    # 1. Program.cs (Privilege Warning)
    prog_cs = repo_path / "src" / "BizHawk.Client.EmuHawk" / "Program.cs"
    if prog_cs.exists():
        with open(prog_cs, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace(
            'title: "This EmuHawk is privileged",',
            'title: "EmuHawk 运行在管理员特权模式",'
        )
        old_priv_msg = 'message: $"EmuHawk detected it {(OSTailoredCode.IsUnixHost ? "is running as root (Superuser)" : "has Administrator privileges")}.\\n"\n\t\t\t\t\t\t\t+ $"Regularly using {(OSTailoredCode.IsUnixHost ? "Superuser" : "Administrator")} for things other than system administration makes it easier to hack you.\\n"\n\t\t\t\t\t\t\t+ "If you\'re certain, you may continue anyway (and without support).\\n"\n\t\t\t\t\t\t\t+ $"You\'ll find a flag \\"{nameof(Config.SkipSuperuserPrivsCheck)}\\" in the config file, which disables this warning.",'
        new_priv_msg = 'message: "EmuHawk 检测到当前正在以管理员权限运行。\\n长期以管理员身份运行非系统管理程序容易增加系统被攻击的风险。\\n如果您确定要继续，可以忽略此提示。\\n您可以在配置文件中设置 \\"SkipSuperuserPrivsCheck\\" 选项以永久关闭此警告。",'
        content = content.replace(old_priv_msg, new_priv_msg)
        with open(prog_cs, "w", encoding="utf-8") as f:
            f.write(content)

    # 2. FileWriteResult.cs (File operation errors)
    fwr_cs = repo_path / "src" / "BizHawk.Client.Common" / "FileWriteResult.cs"
    if fwr_cs.exists():
        with open(fwr_cs, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace('return $"The file \\"{Paths.Final}\\" was written successfully.";', 'return $"文件 \\"{Paths.Final}\\" 已成功保存。";')
        content = content.replace('return $"The temporary file \\"{Paths.Temp}\\" could not be opened.";', 'return $"无法打开临时文件 \\"{Paths.Temp}\\"。";')
        content = content.replace('return $"The file \\"{Paths.Final}\\" could not be created.";', 'return $"无法创建文件 \\"{Paths.Final}\\"。";')
        content = content.replace('return $"An error occurred while writing the file.";', 'return $"写入文件时发生错误。";')
        content = content.replace('return "The operation was aborted.";', 'return "操作已被中止。";')
        content = content.replace('return $"The file \\"{Paths.Final}\\" could not be deleted.";', 'return $"无法删除文件 \\"{Paths.Final}\\"。";')
        content = content.replace('return $"Failed to swap files. Unable to rename \\"{Paths.Temp}\\" to \\"{Paths.Final}\\"";', 'return $"交换文件失败。无法重命名 \\"{Paths.Temp}\\" 为 \\"{Paths.Final}\\"";')
        with open(fwr_cs, "w", encoding="utf-8") as f:
            f.write(content)

    # 3. DialogControllerExtensions.cs
    dce_cs = repo_path / "src" / "BizHawk.Client.Common" / "DialogControllerExtensions.cs"
    if dce_cs.exists():
        with open(dce_cs, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace('caption: "Error",', 'caption: "错误",')
        with open(dce_cs, "w", encoding="utf-8") as f:
            f.write(content)


def apply_patch(repo_path: Path) -> int:
    """
    Patches BizHawk C# source files using the dictionary.
    Returns the total number of replaced strings.
    """
    rules = load_json(RULES_FILE)
    dict_map = get_flattened_dict()
    files = scan_source_files(repo_path, rules)
    
    total_replaced = 0
    patterns = [(p["name"], re.compile(p["regex"])) for p in rules.get("match_patterns", [])]
    
    print(f"[*] Starting patch on {len(files)} source files...")
    
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="utf-8-sig") as f:
                    content = f.read()
            except Exception:
                continue
                
        original_content = content
        file_replaced_count = 0
        
        for name, pattern in patterns:
            def replacer(match):
                nonlocal file_replaced_count
                prefix = match.group(1)
                text = match.group(2)
                suffix = match.group(3)
                
                if text in dict_map:
                    translated = dict_map[text]
                    if translated != text:
                        file_replaced_count += 1
                        return f"{prefix}{translated}{suffix}"
                return match.group(0)
                
            content = pattern.sub(replacer, content)
            
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            total_replaced += file_replaced_count
            
    # Apply specialized hardcoded block patches
    apply_custom_hardcoded_patches(repo_path)
    
    print(f"[+] Patch completed! Total {total_replaced} strings replaced with Chinese.")
    return total_replaced


def main():
    parser = argparse.ArgumentParser(description="BizHawk Chinese Localization Patcher")
    parser.add_argument("--repo-path", type=str, default=".", help="Path to BizHawk repo root")
    parser.add_argument("--extract", action="store_true", help="Extract strings and show missing translations")
    parser.add_argument("--patch", action="store_true", help="Apply Chinese translation patch to source files")
    parser.add_argument("--stats", action="store_true", help="Show translation coverage statistics")
    
    args = parser.parse_args()
    repo_path = Path(args.repo_path).resolve()
    
    dict_map = get_flattened_dict()
    print(f"[*] Loaded dictionary with {len(dict_map)} entries.")
    
    if args.extract or args.stats:
        print(f"[*] Scanning BizHawk source files in: {repo_path}")
        all_strs, missing_strs = extract_strings(repo_path)
        print(f"[=] Total UI strings extracted: {len(all_strs)}")
        print(f"[=] Translated: {len(all_strs) - len(missing_strs)}")
        print(f"[=] Missing: {len(missing_strs)}")
        if all_strs:
            coverage = ((len(all_strs) - len(missing_strs)) / len(all_strs)) * 100
            print(f"[=] Coverage: {coverage:.2f}%")
            
        if args.extract and missing_strs:
            missing_file = LOCALE_DIR / "untranslated.json"
            save_json(missing_file, sorted(list(missing_strs)))
            print(f"[+] Saved {len(missing_strs)} missing strings to {missing_file}")
            
    if args.patch:
        apply_patch(repo_path)


if __name__ == "__main__":
    main()
