<div align="center">

# 📦 Folder-MD-Converter

[English](./README.en.md) | [简体中文](./README.md)

A lightweight folder ⇄ Markdown bidirectional conversion tool with a graphical interface. It can export an entire folder into one or more Markdown files, restore spec-compliant Markdown back into a real folder structure, and includes a built-in **AI Output Guide generator** to help other AIs produce restorable content.

</div>

## ✨ Features

- 🖱️ **Graphical Operation** – Based on `tkinter`, simply pick a folder or Markdown file to export or restore, no command line required.
- 📤 **Folder → Markdown** – Recursively walks the directory and generates a Markdown file containing the tree, statistics and full file contents.
- 📥 **Markdown → Folder** – Parses Markdown exported by this tool (single / mother + parts / multiple) and restores the real folder structure and file contents.
- ✂️ **Auto Split** – When the exported content exceeds a configurable threshold, automatically produces one **mother file** and several **part files** for easier reading or feeding to an AI.
- 🧩 **Auto-merge Parts** – When restoring, selecting the mother file will automatically discover and merge all part files in the same folder.
- 🌐 **Multilingual UI** – Built-in support for Simplified Chinese, English, Français, Español, Русский and العربية, switchable with one click.
- 🤖 **AI Guide Generator** – One-click export of a "Folder Markdown Format Specification" that can be sent to other AIs to guide them into producing restorable Markdown.
- 🛡️ **Safe Restore** – Rejects absolute paths, rejects `..` path traversal, handles Windows reserved names, and prevents writing files outside the target directory.
- 🔤 **Smart Encoding Handling** – When exporting, tries `utf-8-sig → utf-8 → gbk → big5 → latin-1` in order, compatible with text files from various environments.
- 🧱 **Binary & Oversized File Protection** – Automatically detects binary files; oversized files are recorded only as metadata without content, avoiding bloated Markdown.
- 🎨 **Markdown-Fence Aware** – If a file's content contains runs of backticks, a longer fence is used automatically to avoid truncation.

## 📁 Project Structure

```markdown
folder-md-converter/
├── folder-md-converter.py                    # Main program (Python script, GUI + all logic)
├── AI_Guide_Folder_Markdown_Format.md        # English AI Output Guide (for other AIs)
├── AI输出规范_文件夹Markdown格式.md            # Chinese AI Output Guide (for other AIs)
├── LICENSE                                   # MIT License
├── README.md                                 # Chinese documentation
└── README.en.md                              # English documentation (this file)
```

- **Single-file program** – All logic (export, split, restore, AI guide generation, multilingual) is contained in one Python script, no extra dependencies, copy and run.
- **Bundled AI Guides** – Two AI Output Guide files (Chinese & English) are shipped with the repository and can be sent directly to other AIs, no need to generate them manually.

## 🚀 How to Use

### Requirements

- Python 3.8 or higher
- Standard library modules (no extra installation needed):
  - `tkinter` (bundled with official Windows / macOS installers; on Debian/Ubuntu run `sudo apt install python3-tk`)
  - `os`, `re`, `threading`, `traceback`, `pathlib`, `datetime`

### 1. Run the Program

In your terminal:

```bash
python folder-md-converter.py
```

A tabbed window opens, with a **language dropdown** and a **Generate AI Guide** button in the top toolbar.

### 2. Export: Folder → Markdown

1. Switch to the **Export** tab.
2. Click **Choose…** to select the target folder.
3. Optional settings:
   - Include hidden files / folders (starting with `.`).
   - Max file content size (MB, 0 = no limit).
   - Split threshold (MB, 0 = no split).
4. Click **Start Export** and choose where to save the mother file.
5. When done:
   - If under the threshold: a single Markdown file is produced.
   - If over the threshold: one mother file + several `xxx_partNN.md` part files are produced.

### 3. Restore: Markdown → Folder

1. Switch to the **Restore** tab.
2. Click **Choose md files…** to select one or more Markdown files.
   - **Selecting only the mother file is enough** – the program will automatically discover and merge all part files in the same folder.
3. Choose the target folder under **Restore to folder**.
4. Click **Start Restore**; progress and logs are shown in real time.

### 4. Use the AI Guide Files

- Two guide files are bundled with the repository:
  - **`AI输出规范_文件夹Markdown格式.md`** – Chinese version
  - **`AI_Guide_Folder_Markdown_Format.md`** – English version
- Send the appropriate one to other AIs (ChatGPT, Claude, Gemini, DeepSeek, etc.) and they will be able to produce Markdown that this tool can restore.
- You can also click **Generate AI Guide** in the toolbar to export it again:
  - Chinese UI exports the Chinese version;
  - Other languages export the English version.

## 📄 Markdown Format Specification (Core)

This tool uses a **lightweight, human-readable, AI-generatable** Markdown format. The core rules are:

### File Content Block (Mandatory)

Each file starts with a block header, with the path inside backticks:

```markdown
### 1. `src/main.py`
```

- `N` starts at 1 and increments globally.
- The path is **relative to the root folder**, using `/` as separator.
- The path must not be absolute and must not contain `..`.

### Content (Mandatory)

Content is wrapped in a code fence with at least 3 backticks:

```markdown
```python
print("hello")
```
```

### Encoding Marker (Optional)

If the file is not UTF-8, add an HTML comment:

```markdown
<!-- 文件编码：gbk -->
```

The English form `<!-- encoding: gbk -->` is also accepted.

### Binary / Oversized File (Optional)

Use a `> note` instead of content:

```markdown
### 3. `logo.png`

- name: `logo.png`
- size: 12.34 KB

> binary file, no content exported.

---
```

During restore, such files are created as empty placeholders.

### Complete Example

```markdown
# Folder export: demo

- **root**: `/tmp/demo`
- **exported**: 2026-01-01 12:00:00
- **files**: 2
- **folders**: 1
- **include_hidden**: False
- **max_file_mb**: 10.0
- **split_mb**: 0

---

## 1. Tree

```
demo/
├── src/
│   └── main.py
└── README.md
```

---

## 2. Contents

### 1. `README.md`

- name: `README.md`
- rel: `README.md`
- size: 15 B

<!-- encoding: utf-8 -->

```text
# Demo
Hello, world!
```

---

### 2. `src/main.py`

- name: `main.py`
- rel: `src/main.py`
- size: 20 B

<!-- encoding: utf-8 -->

```python
print("hello world")
```

---
```

### Split Output (Optional)

For very long content, split into one mother file and several parts:

- **Mother file**: contains metadata, tree and an index table:
  
  ```markdown
  | Part | Range | Count | Link |
  |:---|:---|---:|:---|
  | `xxx_part01.md` | 1 - 120 | 120 | [Open](./xxx_part01.md) |
  ```

- **Part files**: named `<mother_name>_partNN.md`, containing several `### N. \`path\`` blocks (numbering is globally continuous).
  The restore tool will auto-discover and merge all parts.

## 🎨 Customization & Extension

- **Change the code-block language map**: edit the `EXT_LANG_MAP` and `SPECIAL_FILES` dictionaries to add new extensions or special filenames.
- **Change the header metadata**: edit the `_build_header` function to customize the fields shown at the top of the mother file.
- **Change part file naming**: edit the `part_name` format string inside `generate_markdown`.
- **Add a new UI language**: add a language code to `LANGS` and fill in the corresponding keys in `TRANSLATIONS`.
- **Extend the restore parser**: `parse_markdown_text` extracts file blocks from Markdown; extend it as needed to support additional custom syntax.

## 🌐 Platform & Compatibility

- **Platforms**: Windows / macOS / Linux, runs anywhere `tkinter` is available and Python ≥ 3.8.
- **Output format**: standard Markdown, compatible with any Markdown renderer (GitHub, Typora, Obsidian, VS Code, etc.).
- **AI compatibility**: the bundled Chinese and English guide files are understood by all major LLMs (ChatGPT, Claude, Gemini, DeepSeek, etc.) and can be used as part of a system prompt.
- **Arabic UI**: text is localized, but since `tkinter` has limited RTL support, widget layout remains LTR.

## 🧠 Technical Highlights

- **Streamed Traversal & Sorting** – `walk_sorted` performs a depth-first walk, listing subfolders before files within each directory, each sorted by name, guaranteeing the tree and content order match.
- **Background Thread + Main-Thread Callback** – Export and restore run in separate threads; progress is refreshed in the main thread via `root.after`, so the UI never freezes on long tasks.
- **Pre-Planned Splitting** – Before exporting, the tool collects size estimates for every file and then accumulates in order, cutting a new part as soon as the threshold would be exceeded, avoiding a single oversized chunk.
- **Path Traversal Protection** – `safe_join` rejects absolute paths, `..` paths, and any path that would escape the target directory; Windows reserved names are automatically prefixed with `_`.
- **Encoding Fallback** – Files are read with a multi-encoding fallback list; on write, the encoding recorded in the Markdown is preferred, falling back to UTF-8 if unavailable.
- **Adaptive Fences** – `safe_fence` scans for the longest run of backticks in the content and returns a fence at least one backtick longer, preventing the Markdown from being truncated unexpectedly.

## ⚠️ Limitations

- Text files are **loaded entirely into memory**. Very large single files (>500 MB) may exhaust memory; combine with the *Max file content size* option so only metadata is recorded.
- **Binary files are not exported**; on restore they are recreated as empty placeholders, so the original bytes cannot be fully recovered.
- **The Arabic UI** is not fully RTL-mirrored due to `tkinter` limitations.
- **File permissions and timestamps are not preserved**; only file contents and folder structure are restored.

## 📄 License

This project is open-source under the [MIT License](https://opensource.org/licenses/MIT). You are free to use, modify, and distribute it.

## 🤝 Contributing

Issues and pull requests are welcome!

## 📧 Contact

For questions, please open a GitHub issue.

**Enjoy converting! 📦 → 📄**
