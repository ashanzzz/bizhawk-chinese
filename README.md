# BizHawk-Chinese (BizHawk 中文全量汉化与持续同步项目)

<p align="center">
  <img src="https://raw.githubusercontent.com/TASEmulators/BizHawk/master/src/BizHawk.Client.EmuHawk/Resources/BizHawk_Open.ico" width="80" alt="BizHawk Logo" />
</p>

<p align="center">
  <b>基于官方 <a href="https://github.com/TASEmulators/BizHawk">TASEmulators/BizHawk</a> 的自动化中文本地化流水线</b><br>
  ⚡ 官方更新自动同步 · 🤖 AI 智能增量翻译 · 🎮 TAS 专业词典体系 · 📦 GitHub Actions 自动编译与 Release 发布
</p>

---

## 🌟 项目亮点

1. **零滞后自动同步**：每天通过 GitHub Actions 自动监听并合并官方主仓库最新提交与 Release。
2. **源码级精准 AST 补丁**：自动扫描并安全替换 WinForms 控件文本（菜单、工具栏、对话框、提示等），绝不破坏 Lua API 与模拟内核代码。
3. **高精度 TAS 词典**：包含上百条针对 TAS 速通、内存调试（RAM Watch/Search）、录像编辑（TAStudio）的规范术语。
4. **AI 增量自愈翻译**：官方新增菜单或功能时，自动调用大模型（Gemini / OpenAI / DeepL）翻译新词条并回写词典库。
5. **一键 Release 下载**：无需用户自行配置 C# 编译环境，GitHub Release 自动提供打包好的 Windows x64 绿色免安装中文版。

---

## 📁 目录结构

```text
bizhawk-chinese/
├── .github/workflows/
│   ├── auto_sync_and_translate.yml  # 定时同步上游、提取翻译并提交推送
│   └── build_release.yml            # 自动编译并打包发布 GitHub Release
├── locale/
│   ├── zh_CN.json                   # TAS 专业术语与核心 UI 人工校准词典
│   ├── rules.json                   # 语法树扫描、正则匹配与保护黑名单规则
│   └── auto_generated.json          # AI 增量自动生成的词典池
├── tools/
│   ├── bizhawk_patcher.py           # 词条扫描、提取与源码替换打补丁引擎
│   ├── ai_translate.py              # AI 增量翻译驱动（支持 Gemini/OpenAI/DeepL）
│   └── sync_and_patch.py            # 本地与 CI 流水线一键调度器
└── README.md
```

---

## 🚀 如何部署并上传到您的 GitHub

### 步骤 1：在 GitHub 上创建新仓库
1. 登录您的 GitHub 账号，点击右上角 **New repository**；
2. 仓库名称填入 `bizhawk-chinese`（或您喜欢的名字）；
3. 设置为 **Public**（公开），不需要勾选 Initialize with README。

### 步骤 2：在本地初始化并推送到 GitHub
在当前项目根目录下打开终端（PowerShell 或 Bash），运行：

```bash
# 1. 初始化本地 Git
git init
git add .
git commit -m "feat: initial commit for BizHawk-Chinese localization pipeline"

# 2. 关联您的 GitHub 远程仓库 (将 YOUR_USERNAME 替换为您的 GitHub 用户名)
git remote add origin https://github.com/YOUR_USERNAME/bizhawk-chinese.git
git branch -M master
git push -u origin master
```

### 步骤 3：配置 GitHub Secrets（用于 AI 自动翻译）
1. 打开您的 GitHub 仓库页面 ➔ **Settings** ➔ **Secrets and variables** ➔ **Actions**；
2. 点击 **New repository secret**，添加以下密钥（至少配置一项）：
   - `GEMINI_API_KEY`：Google Gemini API Key（推荐，速度快）
   - 或 `OPENAI_API_KEY`：OpenAI API Key

> [!NOTE]
> 如果不配置 API Key，系统会自动使用免费翻译后备通道进行增量词条翻译。

---

## 🛠️ 本地运行与开发指南

### 1. 扫描与提取未翻译词条
```bash
python tools/bizhawk_patcher.py --repo-path . --extract
```

### 2. 运行 AI 增量翻译
```bash
# 设置环境变量（如使用 Gemini）
set GEMINI_API_KEY=your_key_here
python tools/ai_translate.py
```

### 3. 应用中文补丁到源码
```bash
python tools/bizhawk_patcher.py --repo-path . --patch
```

### 4. 一键完整流水线
```bash
python tools/sync_and_patch.py --repo-path .
```

---

## 📄 开源与协议说明

- 本项目的汉化与自动化工具链代码遵循 [MIT License](LICENSE)。
- BizHawk 模拟器本体代码版权归 [TASEmulators](https://github.com/TASEmulators/BizHawk) 及各大开源模拟器核心作者所有。
