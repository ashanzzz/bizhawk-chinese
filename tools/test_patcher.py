#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Self-test suite for BizHawk Patcher and Rules
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bizhawk_patcher


class TestBizHawkPatcher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_emuhawk_dir = self.temp_dir / "src" / "BizHawk.Client.EmuHawk"
        self.mock_emuhawk_dir.mkdir(parents=True, exist_ok=True)
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_patch_winforms_text(self):
        sample_code = """
        namespace BizHawk.Client.EmuHawk
        {
            public class MainForm : Form
            {
                public void InitializeComponent()
                {
                    this.fileToolStripMenuItem = new ToolStripMenuItem("&File");
                    this.openRomToolStripMenuItem.Text = "&Open ROM...";
                    this.displayFpsMenuItem.Text = "&Display FPS";
                    this.speedUpMenuItem.Text = "Speed &Up";
                    this.btnOk.Text = "OK";
                    this.lblUnk.Text = "Some Untranslated String";
                    MessageBoxEx.Show("Controller Configuration");
                }
            }
        }
        """
        mock_file = self.mock_emuhawk_dir / "MainForm.cs"
        with open(mock_file, "w", encoding="utf-8") as f:
            f.write(sample_code)
            
        all_strs, missing_strs = bizhawk_patcher.extract_strings(self.temp_dir)
        self.assertIn("&File", all_strs)
        self.assertIn("&Open ROM...", all_strs)
        self.assertIn("Some Untranslated String", missing_strs)
        
        # Test patch
        replaced_count = bizhawk_patcher.apply_patch(self.temp_dir)
        self.assertGreater(replaced_count, 0)
        
        with open(mock_file, "r", encoding="utf-8") as f:
            patched_content = f.read()
            
        self.assertIn("文件(&F)", patched_content)
        self.assertIn("打开 ROM(&O)...", patched_content)
        self.assertIn("显示 FPS 帧率(&D)", patched_content)
        self.assertIn("加速(&U)", patched_content)


if __name__ == "__main__":
    unittest.main()
