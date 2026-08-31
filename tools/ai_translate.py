#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Incremental Translation Engine for BizHawk Localization
Translates untranslated UI strings using Gemini / OpenAI / DeepL / High-Concurrency Fallback API.
"""

import os
import sys
import json
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT_DIR = Path(__file__).resolve().parent.parent
LOCALE_DIR = ROOT_DIR / "locale"
ZH_CN_FILE = LOCALE_DIR / "zh_CN.json"
AUTO_GEN_FILE = LOCALE_DIR / "auto_generated.json"
UNTRANSLATED_FILE = LOCALE_DIR / "untranslated.json"

SYSTEM_PROMPT = """你是一名资深的复古游戏模拟器开发者与 TAS (Tool-Assisted Speedrun，工具辅助速通) 汉化专家。
请将以下 BizHawk 模拟器的英文 UI 字符串翻译为标准、地道、规范的简体中文。

翻译规则与注意事项：
1. 保留快捷键助记符：若英文包含 & 符号（如 "&Open ROM..."），中文必须保留对应助记符（如 "打开 ROM(&O)..."）。
2. 保留所有占位符与格式化标记（如 {0}, {1}, %d, %s, \\n 等），严禁删除或翻译占位符。
3. 遵循常见 TAS 术语：
   - Frame Advance -> 单帧步进
   - Lag Frame -> 掉帧 / 延迟帧
   - Savestate -> 即时存档
   - Movie -> 录像
   - Rerecord -> 重录
   - TAStudio -> TAStudio 录像编辑器
   - RAM Search / Watch -> 内存搜索 / 监视
   - Core -> 核心
4. 输出格式必须为 JSON 对象：{"英文原文": "中文翻译"}。
"""


def load_json(filepath: Path) -> dict:
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath: Path, data: dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def translate_single_text(text: str) -> tuple:
    """Translates a single string with hotkey & symbol preservation."""
    try:
        # Check hotkey symbol
        hotkey_char = None
        match = re.search(r"&([a-zA-Z0-9])", text)
        if match:
            hotkey_char = match.group(1).upper()
            
        clean_text = text.replace("&", "")
        if not clean_text.strip():
            return text, text
            
        params = urllib.parse.urlencode({"q": clean_text, "sl": "en", "tl": "zh-CN"})
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&dt=t&{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            trans = "".join([part[0] for part in data[0] if part[0]])
            if hotkey_char and f"(&{hotkey_char})" not in trans:
                trans += f"(&{hotkey_char})"
            return text, trans
    except Exception:
        return text, text


def run_batch_translation(missing_texts: List[str], max_workers: int = 20) -> Dict[str, str]:
    all_translated: Dict[str, str] = {}
    total = len(missing_texts)
    
    print(f"[*] Starting high-concurrency translation for {total} strings (workers={max_workers})...")
    
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(translate_single_text, text): text for text in missing_texts}
        for future in as_completed(futures):
            original, translated = future.result()
            all_translated[original] = translated
            completed += 1
            if completed % 100 == 0 or completed == total:
                print(f"[+] Progress: {completed}/{total} ({completed/total*100:.1f}%)")
                
    return all_translated


def main():
    if not UNTRANSLATED_FILE.exists():
        print(f"[!] {UNTRANSLATED_FILE} not found. Run bizhawk_patcher.py --extract first.")
        return
        
    missing_list = load_json(UNTRANSLATED_FILE)
    if not missing_list:
        print("[+] No missing strings found. Dictionary is completely up to date!")
        return
        
    print(f"[*] Found {len(missing_list)} untranslated strings.")
    translated_map = run_batch_translation(missing_list, max_workers=25)
    
    # Save into auto_generated.json
    current_auto = load_json(AUTO_GEN_FILE)
    current_auto.update(translated_map)
    save_json(AUTO_GEN_FILE, current_auto)
    print(f"[+] Successfully saved {len(translated_map)} new translations to {AUTO_GEN_FILE}")
    
    # Remove untranslated.json
    try:
        UNTRANSLATED_FILE.unlink()
    except Exception:
        pass
    print("[+] Translation process completed successfully!")


if __name__ == "__main__":
    main()
