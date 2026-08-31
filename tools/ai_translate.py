#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Incremental Translation Engine for BizHawk Localization
Translates untranslated UI strings using Gemini / OpenAI / DeepL / Free API with TAS context awareness.
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


def translate_with_gemini(texts: List[str], api_key: str) -> Dict[str, str]:
    """Translates a batch of strings using Google Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"{SYSTEM_PROMPT}\n\n请翻译以下 JSON 列表中的所有英文词条，返回 JSON 键值对：\n{json.dumps(texts, ensure_ascii=False, indent=2)}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    with urllib.request.urlopen(req, timeout=60) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        text_response = res_data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text_response)


def translate_with_openai(texts: List[str], api_key: str, base_url: str = "https://api.openai.com/v1") -> Dict[str, str]:
    """Translates a batch of strings using OpenAI-compatible API."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    
    prompt = f"请翻译以下 JSON 列表中的所有英文词条，返回 JSON 键值对格式：\n{json.dumps(texts, ensure_ascii=False, indent=2)}"
    
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    
    with urllib.request.urlopen(req, timeout=60) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        content = res_data["choices"][0]["message"]["content"]
        return json.loads(content)


def translate_fallback(texts: List[str]) -> Dict[str, str]:
    """Fallback translation using free translation endpoint or heuristic rule."""
    results = {}
    for text in texts:
        try:
            # Preserve hotkeys like &File -> File
            clean_text = text.replace("&", "")
            params = urllib.parse.urlencode({"q": clean_text, "sl": "en", "tl": "zh-CN"})
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&dt=t&{params}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                trans = "".join([part[0] for part in data[0] if part[0]])
                if "&" in text:
                    # restore hotkey
                    hotkey_char = re.search(r"&([a-zA-Z])", text)
                    if hotkey_char:
                        trans += f"(&{hotkey_char.group(1).upper()})"
                results[text] = trans
            time.sleep(0.1)
        except Exception:
            results[text] = text
    return results


def run_batch_translation(missing_texts: List[str], chunk_size: int = 50) -> Dict[str, str]:
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    openai_base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    all_translated: Dict[str, str] = {}
    total = len(missing_texts)
    
    print(f"[*] Starting AI translation for {total} strings...")
    
    for i in range(0, total, chunk_size):
        chunk = missing_texts[i:i + chunk_size]
        print(f"[*] Processing batch {i + 1}-{min(i + chunk_size, total)} of {total}...")
        
        batch_result = {}
        if gemini_key:
            try:
                batch_result = translate_with_gemini(chunk, gemini_key)
            except Exception as e:
                print(f"[Warning] Gemini translation error: {e}, falling back...")
        elif openai_key:
            try:
                batch_result = translate_with_openai(chunk, openai_key, openai_base)
            except Exception as e:
                print(f"[Warning] OpenAI translation error: {e}, falling back...")
                
        if not batch_result:
            print("[*] Using fallback translator...")
            batch_result = translate_fallback(chunk)
            
        all_translated.update(batch_result)
        time.sleep(0.5)
        
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
    translated_map = run_batch_translation(missing_list)
    
    # Save into auto_generated.json
    current_auto = load_json(AUTO_GEN_FILE)
    current_auto.update(translated_map)
    save_json(AUTO_GEN_FILE, current_auto)
    print(f"[+] Saved {len(translated_map)} new translations to {AUTO_GEN_FILE}")
    
    # Remove untranslated.json
    try:
        UNTRANSLATED_FILE.unlink()
    except Exception:
        pass
    print("[+] Translation process finished successfully!")


if __name__ == "__main__":
    main()
