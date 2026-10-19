<div align="center">

# ⃤ L I N K A U D I T ⃤

### *Find every broken and dead link in your docs - one command.*

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![OS](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Stars](https://img.shields.io/github/stars/MrHacker-X/linkaudit?style=flat-square&color=orange)
![Forks](https://img.shields.io/github/forks/MrHacker-X/linkaudit?style=flat-square&color=cyan)

</div>

---

## 📋 Table of Contents

- [🎯 Why LinkAudit?](#-why-linkaudit)
- [🧭 What It Does](#-what-it-does)
- [🚀 Quick Start](#-quick-start)
- [🖼️ Preview](#-preview)
- [📦 Installation](#-installation)
- [✨ Features](#-features)
- [⌨️ Usage](#%EF%B8%8F-usage)
- [⚙️ Configuration](#%EF%B8%8F-configuration)
- [🧰 Tech Stack](#-tech-stack)
- [⚠️ Disclaimer](#%EF%B8%8F-disclaimer)
- [🤝 Contributing](#-contributing)
- [📜 License](#-license)
- [👨‍💻 Developer](#-developer)

---

## 🎯 Why LinkAudit?

> Documentation that links to nothing destroys your readers' trust faster than missing sections. **LinkAudit catches it in two commands**: point it at a Markdown (or plain text) file and it extracts every link, verifies each one, and hands you a report sorted into working / broken / timeouts.
>
> **It's built for writers and maintainers.** `python linkaudit.py notes.md` fits between drafts, and handles `http(s)`, anchors, relative paths, and anchors-within-files the same way.

---

## 🧭 What It Does

| # | Task | What it gives you |
|---|------|-------------------|
| 1️⃣ | Extract every link | All hrefs from Markdown/text, including relative paths, anchors, and URLs |
| 2️⃣ | Verify each link | HEAD/GET classification: `working`, `broken`, `timeout`, or `unknown` |
| 3️⃣ | Export a report | Save the full audit as a JSON/CSV/text report for CI or review |
| 4️⃣ | Interactive or direct CLI | Same audit through a friendly menu or a flag-driven command |

---

## 🚀 Quick Start

```bash
git clone https://github.com/MrHacker-X/linkaudit.git
cd linkaudit
pip install -r requirements.txt
python linkaudit.py                 # interactive menu
```

---

## 🖼️ Preview

<div align="center">

![LinkAudit Preview](https://i.ibb.co/NnGw5zfw/linkaudit.png)

</div>

---

## 📦 Installation

```bash
# 1. clone
git clone https://github.com/MrHacker-X/linkaudit.git
cd linkaudit

# 2. install dependencies
pip install -r requirements.txt

# 3. run
python linkaudit.py
```

### Supported Systems

| OS | Status | Notes |
|----|--------|-------|
| 🐧 Linux | ✅ Fully supported | Any distro with Python 3.8+ |
| 🪟 Windows | ✅ Fully supported | Python from python.org, then the steps above |
| 🍎 macOS | ✅ Fully supported | `brew install python`, then the steps above |
| 📱 Termux (Android) | ✅ Fully supported | `pkg install python`, then the steps above |

> 💡 LinkAudit only *reads* the page behind each link - nothing is written and no requests go out beyond the verification HEAD/GET calls themselves.

---

## ✨ Features

| | Feature | Description |
|---|---------|-------------|
| 🔍 | **Link extraction** | Pulls every ``[]()`` reference out of Markdown, including relative paths and file anchors |
| 🩺 | **Real verification** | Each URL gets an HTTP HEAD (and falls back to GET) with proper status classification |
| 🗂️ | **Sorted verdicts** | Results grouped into working / broken / timeout so you only fix what needs fixing |
| 💾 | **Exportable reports** | Save the full audit as JSON/CSV/text for CI, dashboards, or community review |
| 🎛️ | **Two modes** | A guided interactive menu or a fully flag-driven direct CLI |
| 🛡️ | **Browser-like requests** | Sends a real User-Agent so bot-hostile servers don't misreport your links |
| 🧱 | **Graceful timeouts** | A hanging server becomes one "timeout" line, not a frozen tool |
| 🪶 | **Minimal dependencies** | `requests` + `rich`, nothing else |

---

## ⌨️ Usage

```bash
python linkaudit.py                 # interactive menu
python linkaudit.py -h              # help
python linkaudit.py -v              # version
```

### Direct CLI

```bash
# audit every link in a Markdown file (local + external)
python linkaudit.py README.md

# audit a whole website, internal links only
python linkaudit.py https://example.com --internal-only

# export a detailed JSON/CSV/TXT report
python linkaudit.py docs/ -e link_report.json
```

| Option | Values / Example | Meaning |
|--------|------------------|---------|
| `target` | URL, `.md` file, or docs directory | What to audit (positional) |
| `--internal-only` | flag | Check only internal/local links |
| `--external-only` | flag | Check only external HTTP(S) links |
| `--timeout` | seconds (default 10) | Per-request timeout |
| `-w` / `--workers` | number (default 8) | Concurrent link-check threads |
| `-e` / `--export` | a filename | Save a detailed report (extension decides format) |

---

## ⚙️ Configuration

Audit behavior lives in [`core/config.py`](core/config.py):

| Setting | Default | Effect |
|---------|---------|--------|
| Request headers | browser-like User-Agent | Keeps bot-hostile servers from misreporting |
| Default timeout | short | Seconds each link check waits before giving up |
| Status map | HTTP codes → verdicts | Which codes count as working / broken |
| Anchor patterns | Markdown link regex | How links are extracted from the source file |

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.8+ |
| HTTP | `requests` (HEAD/GET link verification) |
| Parsing | Python standard library regex (link extraction) |
| UI | `rich` (menus, colored tables, prompts) |

---

## ⚠️ Disclaimer

> ### Read this before using LinkAudit.
>
> 1. **Audit your own docs.** Swarming a third-party site with link checks for thousands of URLs is just a benign-DBA version of a flood. Keep your scans reasonable and single-shot.
> 2. **Statuses aren't truth.** Some servers return 200 for soft-404 pages, and bot-blocking CDNs can misreport. Always spot-check flagged links manually.
> 3. **Privacy.** Every link in the file you scan is contacted at least once. Don't feed it files containing URLs you don't want touched.
> 4. **No warranty.** LinkAudit is provided "as is", with no warranty of any kind. The author is **not liable** for misuse or damage from using this tool.

---

## 🤝 Contributing

Contributions are welcome!

```bash
# 1. fork it
# 2. create your branch
git checkout -b feature/amazing-feature
# 3. commit
git commit -m "Add amazing feature"
# 4. push
git push origin feature/amazing-feature
# 5. open a Pull Request
```

---

## 📜 License

LinkAudit is the original project by MrHacker-X - see the [`LICENSE`](https://github.com/MrHacker-X/linkaudit) file in the upstream repository for details.

---

## 👨‍💻 Developer

| | |
|---|---|
| **Dev** | MrHacker-X |
| **GitHub** | [github.com/MrHacker-X](https://github.com/MrHacker-X) |
| **Email** | [contact@vritrasec.com](mailto:contact@vritrasec.com) |
| **Website** | [vritrasec.com](https://vritrasec.com) |
| **Network** | [link.vritrasec.com](https://link.vritrasec.com) |

---

<div align="center">

### ⭐ Star the repo if LinkAudit kept your docs honest ⭐

*Built by MrHacker-X - audit responsibly, fix loudly.*

</div>
