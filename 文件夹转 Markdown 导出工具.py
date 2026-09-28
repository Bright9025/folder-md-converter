#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件夹 <-> Markdown 互转工具
- 导出：文件夹 → Markdown（支持按大小拆分母文件 / 子文件）
- 还原：Markdown（单个 / 母+子 / 多个） → 文件夹
- 生成 AI 规范文件，供其他 AI 按格式输出
"""

import os
import re
import threading
import traceback
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ==================== 语言映射 ====================
EXT_LANG_MAP = {
    '.py': 'python', '.pyw': 'python',
    '.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
    '.ts': 'typescript', '.tsx': 'tsx', '.jsx': 'jsx',
    '.java': 'java', '.kt': 'kotlin', '.scala': 'scala',
    '.c': 'c', '.h': 'c',
    '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.hpp': 'cpp', '.hxx': 'cpp',
    '.cs': 'csharp', '.go': 'go', '.rs': 'rust',
    '.rb': 'ruby', '.php': 'php', '.swift': 'swift',
    '.html': 'html', '.htm': 'html', '.xhtml': 'html',
    '.css': 'css', '.scss': 'scss', '.sass': 'sass', '.less': 'less',
    '.json': 'json', '.jsonc': 'json', '.xml': 'xml', '.svg': 'xml',
    '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml',
    '.ini': 'ini', '.cfg': 'ini', '.conf': 'ini',
    '.md': 'markdown', '.markdown': 'markdown',
    '.sh': 'bash', '.bash': 'bash', '.zsh': 'bash',
    '.bat': 'batch', '.cmd': 'batch', '.ps1': 'powershell',
    '.sql': 'sql', '.r': 'r', '.lua': 'lua', '.pl': 'perl',
    '.vue': 'vue', '.svelte': 'svelte',
    '.txt': 'text', '.log': 'text', '.csv': 'csv', '.tsv': 'tsv',
    '.tex': 'latex', '.bib': 'bibtex',
    '.asm': 'asm', '.s': 'asm',
    '.dart': 'dart', '.ex': 'elixir', '.exs': 'elixir',
    '.erl': 'erlang', '.hrl': 'erlang',
    '.clj': 'clojure', '.cljs': 'clojure',
    '.hs': 'haskell', '.ml': 'ocaml', '.nim': 'nim', '.zig': 'zig',
    '.gradle': 'groovy', '.groovy': 'groovy',
    '.proto': 'protobuf', '.graphql': 'graphql', '.gql': 'graphql',
}
SPECIAL_FILES = {
    'dockerfile': 'dockerfile', 'makefile': 'makefile',
    'gnumakefile': 'makefile', 'cmakelists.txt': 'cmake',
    '.gitignore': 'gitignore', '.gitattributes': 'gitignore',
    '.env': 'bash', '.editorconfig': 'ini', '.npmrc': 'ini',
    'go.mod': 'go', 'cargo.toml': 'toml', 'cargo.lock': 'toml',
}


# ==================== 工具函数 ====================
def get_language(fpath: Path) -> str:
    name_lower = fpath.name.lower()
    if name_lower in SPECIAL_FILES:
        return SPECIAL_FILES[name_lower]
    return EXT_LANG_MAP.get(fpath.suffix.lower(), '')


def is_binary_file(fpath: Path, blocksize: int = 8192) -> bool:
    try:
        with open(fpath, 'rb') as f:
            chunk = f.read(blocksize)
        return b'\x00' in chunk if chunk else False
    except (OSError, PermissionError):
        return True


def read_text_file(fpath: Path):
    raw = fpath.read_bytes()
    for enc in ('utf-8-sig', 'utf-8', 'gbk', 'big5', 'latin-1'):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', errors='replace'), 'utf-8(replace)'


def safe_fence(content: str) -> str:
    max_run = cur = 0
    for ch in content:
        if ch == '`':
            cur += 1
            max_run = max(max_run, cur)
        else:
            cur = 0
    return '`' * max(3, max_run + 1)


def human_size(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f"{n} B" if unit == 'B' else f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} PB"


def walk_sorted(root: Path, include_hidden: bool = False):
    def _walk(d: Path):
        try:
            entries = list(d.iterdir())
        except (PermissionError, OSError):
            return
        if not include_hidden:
            entries = [e for e in entries if not e.name.startswith('.')]
        dirs = sorted((e for e in entries if e.is_dir()), key=lambda x: x.name.lower())
        files = sorted((e for e in entries if e.is_file()), key=lambda x: x.name.lower())
        for sub in dirs:
            yield from _walk(sub)
        for f in files:
            yield f
    yield from _walk(root)


def generate_tree(root: Path, include_hidden: bool = False) -> str:
    lines = [f"{root.name}/"]

    def _walk(d: Path, prefix: str):
        try:
            entries = list(d.iterdir())
        except (PermissionError, OSError):
            return
        if not include_hidden:
            entries = [e for e in entries if not e.name.startswith('.')]
        dirs = sorted((e for e in entries if e.is_dir()), key=lambda x: x.name.lower())
        files = sorted((e for e in entries if e.is_file()), key=lambda x: x.name.lower())
        items = dirs + files
        for i, item in enumerate(items):
            last = (i == len(items) - 1)
            connector = "└── " if last else "├── "
            suffix = "/" if item.is_dir() else ""
            lines.append(f"{prefix}{connector}{item.name}{suffix}")
            if item.is_dir():
                _walk(item, prefix + ("    " if last else "│   "))

    _walk(root, "")
    return "\n".join(lines)


def count_dirs(root: Path, include_hidden: bool = False) -> int:
    n = 0
    for _, dirnames, _ in os.walk(root):
        if not include_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        n += len(dirnames)
    return n


# ==================== 导出：内容块 ====================
def _build_header(root_dir: Path, total: int, dir_count: int,
                  include_hidden: bool, max_size_mb: float,
                  split_size_mb: float) -> str:
    s = []
    s.append(f"# 文件夹内容导出：{root_dir.name}\n\n")
    s.append(f"- **根目录**：`{root_dir}`\n")
    s.append(f"- **导出时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    s.append(f"- **文件总数**：{total}\n")
    s.append(f"- **文件夹总数**：{dir_count}（不含根目录）\n")
    s.append(f"- **包含隐藏项**：{'是' if include_hidden else '否'}\n")
    s.append(f"- **单文件内容上限**：{'不限制' if not max_size_mb else f'{max_size_mb} MB'}\n")
    s.append(f"- **拆分阈值**：{'不拆分' if not split_size_mb else f'{split_size_mb} MB'}\n\n")
    return "".join(s)


def _file_block(idx: int, fpath: Path, rel: Path, size: int,
                binary: bool, max_bytes: int) -> str:
    out = []
    out.append(f"### {idx}. `{rel.as_posix()}`\n\n")
    out.append(f"- 文件名：`{fpath.name}`\n")
    out.append(f"- 相对路径：`{rel.as_posix()}`\n")
    out.append(f"- 绝对路径：`{fpath}`\n")
    out.append(f"- 文件大小：{human_size(size)}\n\n")

    if binary:
        out.append("> 二进制文件，未导出内容。\n\n---\n\n")
        return "".join(out)
    if max_bytes and size > max_bytes:
        out.append(f"> 文件过大（{human_size(size)}），超过上限，未导出内容。\n\n---\n\n")
        return "".join(out)

    try:
        content, enc = read_text_file(fpath)
    except Exception as e:
        out.append(f"> 读取失败：`{e}`\n\n---\n\n")
        return "".join(out)

    lang = get_language(fpath)
    fence = safe_fence(content)
    out.append(f"<!-- 文件编码：{enc} -->\n\n")
    out.append(f"{fence}{lang}\n")
    out.append(content)
    if not content.endswith('\n'):
        out.append('\n')
    out.append(f"{fence}\n\n---\n\n")
    return "".join(out)


# ==================== 导出主逻辑 ====================
def generate_markdown(
    root_dir: Path, out_path: Path,
    include_hidden: bool = False,
    max_size_mb: float = 10.0,
    split_size_mb: float = 0.0,
    progress_cb=None, cancel_event=None,
) -> dict:
    root_dir = Path(root_dir).resolve()
    out_path = Path(out_path).resolve()
    max_bytes = int(max_size_mb * 1024 * 1024) if max_size_mb > 0 else 0
    split_bytes = int(split_size_mb * 1024 * 1024) if split_size_mb > 0 else 0

    all_files = list(walk_sorted(root_dir, include_hidden))
    total = len(all_files)
    dir_count = count_dirs(root_dir, include_hidden)

    file_info = []
    for fpath in all_files:
        try:
            rel = fpath.relative_to(root_dir)
        except ValueError:
            rel = fpath
        try:
            size = fpath.stat().st_size
        except OSError:
            size = 0
        binary = is_binary_file(fpath)
        content_size = 260 if (binary or (max_bytes and size > max_bytes)) else size + 420
        file_info.append({
            'path': fpath, 'rel': rel, 'size': size,
            'binary': binary, 'content_size': content_size,
        })

    tree_text = generate_tree(root_dir, include_hidden)
    header_text = _build_header(root_dir, total, dir_count,
                                include_hidden, max_size_mb, split_size_mb)
    header_size = len((header_text + tree_text).encode('utf-8')) + 4000
    total_content_size = sum(fi['content_size'] for fi in file_info)

    need_split = split_bytes > 0 and (header_size + total_content_size) > split_bytes
    base_dir = out_path.parent
    base_name = out_path.stem
    parts_written = []
    part_meta = []

    def _write_single(fp, with_index=False):
        fp.write(header_text)
        fp.write("---\n\n## 一、目录结构\n\n```\n")
        fp.write(tree_text)
        fp.write("\n```\n\n---\n\n## 二、文件内容\n\n")
        for idx, fi in enumerate(file_info, 1):
            if cancel_event and cancel_event.is_set():
                fp.write("\n> ⚠️ 用户已取消导出，以下内容不完整。\n")
                break
            if progress_cb:
                progress_cb(idx, total, fi['rel'].as_posix())
            fp.write(_file_block(idx, fi['path'], fi['rel'],
                                 fi['size'], fi['binary'], max_bytes))

    # 规划分块
    chunks = []
    if need_split:
        part_reserve = 400
        cur_start = 0
        cur_size = part_reserve
        for i, fi in enumerate(file_info):
            bs = fi['content_size']
            if i > cur_start and (cur_size + bs) > split_bytes:
                chunks.append((cur_start, i))
                cur_start = i
                cur_size = part_reserve
            cur_size += bs
        if cur_start < len(file_info):
            chunks.append((cur_start, len(file_info)))
        if len(chunks) <= 1:
            need_split = False

    # ========== 单文件模式 ==========
    if not need_split:
        with open(out_path, 'w', encoding='utf-8', newline='\n') as fp:
            _write_single(fp)
        return {
            'files': total, 'dirs': dir_count,
            'output': str(out_path), 'parts': [], 'split': False,
        }

    # ========== 拆分模式 ==========
    n_parts = len(chunks)
    width = max(2, len(str(n_parts)))
    for part_idx, (start, end) in enumerate(chunks, 1):
        if cancel_event and cancel_event.is_set():
            break
        part_name = f"{base_name}_part{part_idx:0{width}d}.md"
        part_path = base_dir / part_name
        parts_written.append(part_path)
        part_files = file_info[start:end]

        with open(part_path, 'w', encoding='utf-8', newline='\n') as fp:
            fp.write(f"# {root_dir.name} - 第 {part_idx}/{n_parts} 部分\n\n")
            fp.write(f"- 母文件：[`{out_path.name}`](./{out_path.name})\n")
            fp.write(f"- 覆盖文件序号：{start + 1} - {end}\n")
            fp.write(f"- 本部分文件数：{len(part_files)}\n\n---\n\n")
            for local_i, fi in enumerate(part_files):
                global_idx = start + local_i + 1
                if cancel_event and cancel_event.is_set():
                    fp.write("\n> ⚠️ 用户已取消导出，以下内容不完整。\n")
                    break
                if progress_cb:
                    progress_cb(global_idx, total, fi['rel'].as_posix())
                fp.write(_file_block(global_idx, fi['path'], fi['rel'],
                                     fi['size'], fi['binary'], max_bytes))

        part_meta.append({
            'name': part_name, 'start': start + 1, 'end': end,
            'count': len(part_files),
        })

    # 母文件
    with open(out_path, 'w', encoding='utf-8', newline='\n') as fp:
        fp.write(header_text)
        fp.write("---\n\n## 一、目录结构\n\n```\n")
        fp.write(tree_text)
        fp.write("\n```\n\n---\n\n## 二、文件内容索引\n\n")
        fp.write(f"由于内容超过拆分阈值（{split_size_mb} MB），"
                 f"已拆分为 **{n_parts}** 个子文件：\n\n")
        fp.write("| 子文件 | 覆盖文件序号 | 文件数 | 链接 |\n")
        fp.write("|:---|:---|---:|:---|\n")
        for m in part_meta:
            fp.write(f"| `{m['name']}` | {m['start']} - {m['end']} "
                     f"| {m['count']} | [打开](./{m['name']}) |\n")
        fp.write("\n> 提示：本母文件包含目录结构与索引，"
                 "具体文件内容请点击上表链接查看。\n")

    return {
        'files': total, 'dirs': dir_count,
        'output': str(out_path),
        'parts': [str(p) for p in parts_written],
        'split': True,
    }


# ==================== 还原：解析 ====================
HEADER_RE = re.compile(r'^###\s+\d+\.\s+`(.+?)`\s*$')
FENCE_RE = re.compile(r'^(`{3,})(\w*)\s*$')
ENC_RE = re.compile(r'<!--\s*文件编码：\s*(.+?)\s*-->')
PART_REF_RE = re.compile(r'\|\s*`([^`]+?\.md)`\s*\|')


def parse_markdown_text(text: str):
    """从 Markdown 文本里提取所有文件块。yield (rel_path, content_or_None, encoding)"""
    lines = text.split('\n')
    n = len(lines)
    i = 0
    while i < n:
        m = HEADER_RE.match(lines[i])
        if not m:
            i += 1
            continue
        rel_path = m.group(1).strip()
        i += 1
        encoding = 'utf-8'
        no_content = False

        # 读取元数据区，直到遇到围栏 / 说明 / 下一个块
        while i < n:
            line = lines[i]
            if HEADER_RE.match(line):
                break
            em = ENC_RE.search(line)
            if em:
                encoding = em.group(1).strip()
                i += 1
                continue
            if FENCE_RE.match(line):
                break
            s = line.strip()
            if s.startswith('> '):
                no_content = True
                while i < n and not HEADER_RE.match(lines[i]):
                    if lines[i].strip() == '---':
                        i += 1
                        break
                    i += 1
                break
            i += 1

        if no_content:
            yield rel_path, None, encoding
            continue

        if i >= n:
            break
        fm = FENCE_RE.match(lines[i])
        if not fm:
            continue
        fence = fm.group(1)
        i += 1
        buf = []
        while i < n:
            if lines[i].rstrip() == fence:
                break
            buf.append(lines[i])
            i += 1
        if i < n:
            i += 1  # 跳过闭围栏
        yield rel_path, '\n'.join(buf), encoding


def discover_parts(md_path: Path):
    """若给定 md 是母文件，返回同目录下所有被引用的子文件路径"""
    try:
        text = md_path.read_text(encoding='utf-8')
    except Exception:
        return []
    found = []
    seen = set()
    for m in PART_REF_RE.finditer(text):
        name = m.group(1).strip()
        if not name.lower().endswith('.md'):
            continue
        if name in seen:
            continue
        seen.add(name)
        p = md_path.parent / name
        if p.exists() and p.is_file() and p != md_path:
            found.append(p)
    return found


def safe_join(base: Path, rel: str) -> Path:
    """防止路径穿越，返回绝对路径"""
    rel_norm = rel.replace('\\', '/').strip()
    if not rel_norm:
        raise ValueError("空路径")
    p = Path(rel_norm)
    if p.is_absolute():
        raise ValueError(f"绝对路径不允许：{rel}")
    clean_parts = []
    for part in p.parts:
        if part in ('', '.'):
            continue
        if part == '..':
            raise ValueError(f"不允许相对路径穿越：{rel}")
        # Windows 保留字
        if os.name == 'nt' and re.match(r'^(CON|PRN|AUX|NUL|COM\d|LPT\d)$',
                                        part, re.IGNORECASE):
            clean_parts.append('_' + part)
        else:
            clean_parts.append(part)
    if not clean_parts:
        raise ValueError(f"无效路径：{rel}")
    target = (base.joinpath(*clean_parts)).resolve()
    base_res = base.resolve()
    try:
        target.relative_to(base_res)
    except ValueError:
        raise ValueError(f"路径越界：{rel}")
    return target


def restore_from_md(md_paths, target_dir: Path,
                    auto_discover_parts: bool = True,
                    progress_cb=None, cancel_event=None) -> dict:
    """把 md 文件还原为文件夹"""
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    # 展开：用户选的母文件 → 自动补充子文件
    expanded = []
    seen_paths = set()
    for mp in md_paths:
        mp = Path(mp).resolve()
        if mp in seen_paths:
            continue
        seen_paths.add(mp)
        expanded.append(mp)
        if auto_discover_parts:
            for sub in discover_parts(mp):
                sub = sub.resolve()
                if sub not in seen_paths:
                    seen_paths.add(sub)
                    expanded.append(sub)

    # 汇总所有块
    entries = []
    errors = []
    for mp in expanded:
        try:
            text = mp.read_text(encoding='utf-8')
        except Exception as e:
            errors.append(f"读取 {mp} 失败：{e}")
            continue
        for rel, content, enc in parse_markdown_text(text):
            entries.append((rel, content, enc, mp.name))

    total = len(entries)
    written = 0
    skipped = []

    for idx, (rel, content, enc, src) in enumerate(entries, 1):
        if cancel_event and cancel_event.is_set():
            break
        if progress_cb:
            progress_cb(idx, total, rel)
        try:
            target = safe_join(target_dir, rel)
        except ValueError as e:
            skipped.append(f"{rel}（{e}）")
            continue

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if content is None:
                target.write_bytes(b'')
            else:
                write_enc = 'utf-8' if enc.startswith('utf-8') else enc
                try:
                    target.write_text(content, encoding=write_enc)
                except LookupError:
                    target.write_text(content, encoding='utf-8')
            written += 1
        except Exception as e:
            skipped.append(f"{rel}（写入失败：{e}）")

    return {
        'written': written, 'total': total,
        'target': str(target_dir),
        'files_scanned': [str(p) for p in expanded],
        'skipped': skipped, 'errors': errors,
    }


# ==================== AI 规范文件 ====================
AI_GUIDE_MD = r'''# 文件夹 Markdown 格式规范（供 AI 参考）

本文件规范一种 Markdown 格式，用于描述一个文件夹的完整内容。
任何 AI 只要按本规范输出，用户即可用「文件夹转 Markdown 导出工具」的
还原功能，把 Markdown 还原成真实的文件夹结构与文件。

---

## 一、整体结构

Markdown 按顺序包含三部分，各部分之间用 `---` 分隔：

```
# 标题与元数据

## 一、目录结构
（代码块形式的目录树）

## 二、文件内容
### 1. `path/to/file1`
（元数据 + 内容）

### 2. `path/to/file2`
（元数据 + 内容）
```

---

## 二、标题与元数据

文件顶部是一级标题，随后是元数据列表：

```markdown
# 文件夹内容导出：myproject

- **根目录**：`/Users/me/myproject`
- **导出时间**：2026-01-01 12:00:00
- **文件总数**：5
- **文件夹总数**：2（不含根目录）
- **包含隐藏项**：否
- **单文件内容上限**：10.0 MB
- **拆分阈值**：不拆分
```

还原主要依据是每个文件块的路径，头部元数据供人类阅读。

---

## 三、目录结构（推荐，非必须）

`## 一、目录结构` 下面放一个代码块，内容是类似 `tree` 命令的目录树。
**还原时不依赖这部分**，但推荐提供，便于人类阅读。

```text
myproject/
├── src/
│   ├── main.py
│   └── utils.py
└── README.md
```

---

## 四、文件内容块（核心）

`## 二、文件内容` 下面是每个文件的块。每个块按以下格式：

### 4.1 块头（强制）

```markdown
### N. `相对路径`
```

- `N` 从 1 开始，全局连续递增。
- 反引号里是**相对于根目录**的路径，使用 `/` 分隔。
- 路径不能是绝对路径，不能包含 `..`。

### 4.2 元数据（可选）

```markdown
- 文件名：`main.py`
- 相对路径：`src/main.py`
- 绝对路径：`/Users/me/myproject/src/main.py`
- 文件大小：1.23 KB
```

**只有 `### N. \`path\`` 这一行是强制的**，还原只看这一行和下面的代码块。

### 4.3 编码标记（可选）

若文件不是 UTF-8，可以加一个 HTML 注释：

```markdown
<!-- 文件编码：gbk -->
```

### 4.4 内容（强制）

内容用**代码围栏**包裹，最少 3 个反引号。

````markdown
```python
print("hello")
```
````

语言标记（`python`、`js` 等）可选，还原时忽略。
**若文件内容本身包含连续反引号，围栏必须比内容里最长的连续反引号更长。**
例如内容里最多有 3 个连续反引号，围栏至少用 4 个。

### 4.5 块尾分隔（推荐）

每个文件块结尾加一行 `---`：

```markdown
### 1. `README.md`

- 文件名：`README.md`

```text
hello
```

---
```

---

## 五、二进制文件与超大文件

若文件是二进制或太大，可以不输出内容，只写说明：

```markdown
### 3. `logo.png`

- 文件名：`logo.png`
- 文件大小：12.34 KB

> 二进制文件，未导出内容。

---
```

还原时这种文件会被创建为空文件（占位）。

---

## 六、完整示例

````markdown
# 文件夹内容导出：demo

- **根目录**：`/tmp/demo`
- **导出时间**：2026-01-01 12:00:00
- **文件总数**：2
- **文件夹总数**：1（不含根目录）
- **包含隐藏项**：否
- **单文件内容上限**：10.0 MB
- **拆分阈值**：不拆分

---

## 一、目录结构

```
demo/
├── src/
│   └── main.py
└── README.md
```

---

## 二、文件内容

### 1. `README.md`

- 文件名：`README.md`
- 相对路径：`README.md`
- 绝对路径：`/tmp/demo/README.md`
- 文件大小：15 B

<!-- 文件编码：utf-8 -->

```text
# Demo
Hello, world!
```

---

### 2. `src/main.py`

- 文件名：`main.py`
- 相对路径：`src/main.py`
- 绝对路径：`/tmp/demo/src/main.py`
- 文件大小：20 B

<!-- 文件编码：utf-8 -->

```python
print("hello world")
```

---
````

---

## 七、AI 输出 Checklist

- [ ] 顶层有一级标题 `# ...`
- [ ] 至少包含 `## 二、文件内容` 段落
- [ ] 每个文件都以 `### N. \`相对路径\`` 开头
- [ ] `N` 从 1 连续递增
- [ ] 路径用正斜杠 `/`，不要用绝对路径，不要含 `..`
- [ ] 内容用代码围栏（至少 3 个反引号）包裹
- [ ] 若内容里含反引号，围栏要更长
- [ ] 二进制 / 超大文件用 `> 说明` 代替内容
- [ ] 各文件块之间用 `---` 分隔
- [ ] **整体不要再用一层代码块包住**（不要整个文件套在 ``` 里）

---

## 八、常见错误

| 错误 | 后果 | 修正 |
|---|---|---|
| 忘记写 `### N. \`path\`` | 该文件不会被还原 | 补上块头 |
| 路径是绝对路径 | 还原失败或越界 | 改成相对根目录的路径 |
| 围栏长度不够 | 内容被截断 | 用更长的围栏 |
| 整个 md 被包在 ``` 里 | 无法解析 | 不要整体包代码块 |
| 文件块之间没有 `---` | 一般不影响，但不清晰 | 加上 `---` |
| 路径里含 `..` | 被拒绝，跳过 | 改成正常相对路径 |

---

## 九、拆分输出（可选）

若内容很长，可拆分为一个母文件和多个子文件：

- **母文件**：包含元数据、目录结构、以及一个索引表：

  ```markdown
  | 子文件 | 覆盖文件序号 | 文件数 | 链接 |
  |:---|:---|---:|:---|
  | `xxx_part01.md` | 1 - 120 | 120 | [打开](./xxx_part01.md) |
  ```

- **子文件**：文件名形如 `<母文件名>_partNN.md`，
  内容为若干 `### N. \`path\`` 块（编号全局连续）。
  还原工具会自动发现并合并所有子文件。
'''


# ==================== GUI ====================
class ExportTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.folder_var = tk.StringVar()
        self.include_hidden_var = tk.BooleanVar(value=False)
        self.max_size_var = tk.StringVar(value="10")
        self.split_size_var = tk.StringVar(value="5")
        self.cancel_event = threading.Event()
        self._build()

    def _build(self):
        row = ttk.Frame(self)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text="目标文件夹：").pack(side='left')
        ttk.Entry(row, textvariable=self.folder_var).pack(
            side='left', fill='x', expand=True, padx=6)
        ttk.Button(row, text="选择…", command=self.choose_folder).pack(side='left')

        opts = ttk.LabelFrame(self, text="选项", padding=10)
        opts.pack(fill='x', pady=6)
        ttk.Checkbutton(
            opts, text="包含隐藏文件 / 文件夹（以 . 开头）",
            variable=self.include_hidden_var,
        ).pack(anchor='w')
        r1 = ttk.Frame(opts); r1.pack(fill='x', pady=(8, 0))
        ttk.Label(r1, text="单文件内容大小上限（MB，0 = 不限制）：").pack(side='left')
        ttk.Entry(r1, textvariable=self.max_size_var, width=8).pack(side='left', padx=6)
        r2 = ttk.Frame(opts); r2.pack(fill='x', pady=(6, 0))
        ttk.Label(r2, text="拆分阈值（MB，0 = 不拆分）：").pack(side='left')
        ttk.Entry(r2, textvariable=self.split_size_var, width=8).pack(side='left', padx=6)
        ttk.Label(r2, text="超过阈值时生成母文件 + 若干子文件",
                  foreground="#666").pack(side='left', padx=6)

        btn_row = ttk.Frame(self); btn_row.pack(fill='x', pady=6)
        self.start_btn = ttk.Button(btn_row, text="开始导出", command=self.start)
        self.start_btn.pack(side='left')
        self.cancel_btn = ttk.Button(btn_row, text="取消",
                                     command=self.cancel, state='disabled')
        self.cancel_btn.pack(side='left', padx=6)

        prog = ttk.LabelFrame(self, text="进度", padding=10)
        prog.pack(fill='both', expand=True, pady=6)
        self.progress = ttk.Progressbar(prog, mode='determinate')
        self.progress.pack(fill='x')
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(prog, textvariable=self.status_var,
                  wraplength=620, justify='left').pack(fill='x', pady=(8, 0))
        log_frame = ttk.Frame(prog); log_frame.pack(fill='both', expand=True, pady=(8, 0))
        self.log = tk.Text(log_frame, height=8, wrap='none')
        self.log.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(log_frame, command=self.log.yview)
        sb.pack(side='right', fill='y')
        self.log.configure(yscrollcommand=sb.set, state='disabled')

    def choose_folder(self):
        p = filedialog.askdirectory(title="选择要导出的文件夹")
        if p:
            self.folder_var.set(p)

    def log_write(self, msg):
        self.log.configure(state='normal')
        self.log.insert('end', msg + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def _parse_float(self, s, default=0.0):
        s = (s or '').strip()
        if not s:
            return default
        v = float(s)
        if v < 0:
            raise ValueError
        return v

    def start(self):
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("提示", "请先选择目标文件夹。"); return
        root_path = Path(folder)
        if not root_path.is_dir():
            messagebox.showerror("错误", "所选路径不是有效文件夹。"); return
        try:
            max_mb = self._parse_float(self.max_size_var.get(), 10.0)
            split_mb = self._parse_float(self.split_size_var.get(), 0.0)
        except ValueError:
            messagebox.showerror("错误", "大小参数必须是 ≥ 0 的数字。"); return

        out_path = filedialog.asksaveasfilename(
            title="保存母文件（Markdown）",
            defaultextension=".md",
            initialfile=f"{root_path.name}_export.md",
            filetypes=[("Markdown 文件", "*.md"), ("所有文件", "*.*")],
        )
        if not out_path:
            return

        self.start_btn.configure(state='disabled')
        self.cancel_btn.configure(state='normal')
        self.progress.configure(value=0, maximum=100)
        self.log.configure(state='normal'); self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')
        self.cancel_event.clear()

        threading.Thread(
            target=self._worker,
            args=(root_path, Path(out_path),
                  self.include_hidden_var.get(), max_mb, split_mb),
            daemon=True,
        ).start()

    def _worker(self, root_path, out_path, include_hidden, max_mb, split_mb):
        try:
            def cb(cur, total, name):
                step = max(1, total // 200) if total > 200 else 1
                if cur % step != 0 and cur != total:
                    return
                pct = (cur / total * 100) if total else 100.0
                self.after(0, lambda: self._update_progress(cur, total, name, pct))

            result = generate_markdown(
                root_path, out_path,
                include_hidden=include_hidden,
                max_size_mb=max_mb, split_size_mb=split_mb,
                progress_cb=cb, cancel_event=self.cancel_event,
            )
            self.after(0, lambda: self._done(result))
        except Exception as e:
            err = traceback.format_exc()
            self.after(0, lambda: self._error(e, err))

    def _update_progress(self, cur, total, name, pct):
        self.progress.configure(value=pct)
        self.status_var.set(f"[{cur}/{total}] {name}")
        if cur == 1 or cur == total or cur % 20 == 0:
            self.log_write(f"[{cur}/{total}] {name}")

    def _done(self, r):
        self.start_btn.configure(state='normal')
        self.cancel_btn.configure(state='disabled')
        self.progress.configure(value=100)
        if r['split']:
            self.status_var.set(
                f"完成：{r['files']} 个文件 / {r['dirs']} 个文件夹，"
                f"拆分为 {len(r['parts'])} 个子文件")
            self.log_write(f"✅ 母文件：{r['output']}")
            for p in r['parts']:
                self.log_write(f"   ├─ {p}")
            messagebox.showinfo("完成",
                f"导出完成（已拆分）！\n\n文件数：{r['files']}\n"
                f"文件夹数：{r['dirs']}\n子文件数：{len(r['parts'])}\n\n"
                f"母文件：\n{r['output']}")
        else:
            self.status_var.set(f"完成：{r['files']} 个文件，{r['dirs']} 个文件夹")
            self.log_write(f"✅ 已导出到：{r['output']}")
            messagebox.showinfo("完成",
                f"导出完成！\n\n文件数：{r['files']}\n"
                f"文件夹数：{r['dirs']}\n\n输出文件：\n{r['output']}")

    def _error(self, e, err):
        self.start_btn.configure(state='normal')
        self.cancel_btn.configure(state='disabled')
        self.status_var.set("发生错误")
        self.log_write(err)
        messagebox.showerror("错误", f"导出失败：{e}")

    def cancel(self):
        self.cancel_event.set()
        self.status_var.set("正在取消…")


class RestoreTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.md_paths = []
        self.target_var = tk.StringVar()
        self.auto_parts_var = tk.BooleanVar(value=True)
        self.cancel_event = threading.Event()
        self._build()

    def _build(self):
        info = ttk.Label(
            self,
            text="选择由本工具导出的 Markdown 文件（可多选）。"
                 "若选择母文件，将自动发现同目录下的所有子文件。",
            foreground="#555", wraplength=680, justify='left',
        )
        info.pack(fill='x', pady=(0, 8))

        row = ttk.Frame(self); row.pack(fill='x', pady=4)
        ttk.Button(row, text="选择 md 文件…", command=self.choose_md).pack(side='left')
        ttk.Button(row, text="清空列表", command=self.clear_md).pack(side='left', padx=6)
        self.count_var = tk.StringVar(value="已选 0 个文件")
        ttk.Label(row, textvariable=self.count_var, foreground="#666").pack(side='left', padx=8)

        list_frame = ttk.LabelFrame(self, text="已选文件", padding=8)
        list_frame.pack(fill='both', expand=True, pady=6)
        self.file_list = tk.Listbox(list_frame, height=6)
        self.file_list.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(list_frame, command=self.file_list.yview)
        sb.pack(side='right', fill='y')
        self.file_list.configure(yscrollcommand=sb.set)

        row2 = ttk.Frame(self); row2.pack(fill='x', pady=6)
        ttk.Label(row2, text="还原到文件夹：").pack(side='left')
        ttk.Entry(row2, textvariable=self.target_var).pack(
            side='left', fill='x', expand=True, padx=6)
        ttk.Button(row2, text="选择…", command=self.choose_target).pack(side='left')

        ttk.Checkbutton(
            self, text="自动发现同目录下的子文件（母文件拆分场景）",
            variable=self.auto_parts_var,
        ).pack(anchor='w', pady=4)

        btn_row = ttk.Frame(self); btn_row.pack(fill='x', pady=6)
        self.start_btn = ttk.Button(btn_row, text="开始还原", command=self.start)
        self.start_btn.pack(side='left')
        self.cancel_btn = ttk.Button(btn_row, text="取消",
                                     command=self.cancel, state='disabled')
        self.cancel_btn.pack(side='left', padx=6)

        prog = ttk.LabelFrame(self, text="进度", padding=10)
        prog.pack(fill='both', expand=True, pady=6)
        self.progress = ttk.Progressbar(prog, mode='determinate')
        self.progress.pack(fill='x')
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(prog, textvariable=self.status_var,
                  wraplength=620, justify='left').pack(fill='x', pady=(8, 0))
        log_frame = ttk.Frame(prog); log_frame.pack(fill='both', expand=True, pady=(8, 0))
        self.log = tk.Text(log_frame, height=8, wrap='none')
        self.log.pack(side='left', fill='both', expand=True)
        sb2 = ttk.Scrollbar(log_frame, command=self.log.yview)
        sb2.pack(side='right', fill='y')
        self.log.configure(yscrollcommand=sb2.set, state='disabled')

    def choose_md(self):
        paths = filedialog.askopenfilenames(
            title="选择要还原的 md 文件",
            filetypes=[("Markdown 文件", "*.md"), ("所有文件", "*.*")],
        )
        if paths:
            for p in paths:
                if p not in self.md_paths:
                    self.md_paths.append(p)
            self._refresh_list()

    def clear_md(self):
        self.md_paths.clear()
        self._refresh_list()

    def _refresh_list(self):
        self.file_list.delete(0, 'end')
        for p in self.md_paths:
            self.file_list.insert('end', p)
        self.count_var.set(f"已选 {len(self.md_paths)} 个文件")

    def choose_target(self):
        p = filedialog.askdirectory(title="选择还原到的文件夹")
        if p:
            self.target_var.set(p)

    def log_write(self, msg):
        self.log.configure(state='normal')
        self.log.insert('end', msg + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def start(self):
        if not self.md_paths:
            messagebox.showwarning("提示", "请先选择要还原的 md 文件。"); return
        target = self.target_var.get().strip()
        if not target:
            messagebox.showwarning("提示", "请选择还原到的目标文件夹。"); return
        target_path = Path(target)
        target_path.mkdir(parents=True, exist_ok=True)

        if not messagebox.askyesno(
            "确认",
            f"将把 md 文件内容还原到：\n{target_path}\n\n"
            f"同名文件会被覆盖，是否继续？"
        ):
            return

        self.start_btn.configure(state='disabled')
        self.cancel_btn.configure(state='normal')
        self.progress.configure(value=0, maximum=100)
        self.log.configure(state='normal'); self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')
        self.cancel_event.clear()

        threading.Thread(
            target=self._worker,
            args=(list(self.md_paths), target_path, self.auto_parts_var.get()),
            daemon=True,
        ).start()

    def _worker(self, md_paths, target_path, auto_parts):
        try:
            def cb(cur, total, name):
                step = max(1, total // 200) if total > 200 else 1
                if cur % step != 0 and cur != total:
                    return
                pct = (cur / total * 100) if total else 100.0
                self.after(0, lambda: self._update_progress(cur, total, name, pct))

            result = restore_from_md(
                md_paths, target_path,
                auto_discover_parts=auto_parts,
                progress_cb=cb, cancel_event=self.cancel_event,
            )
            self.after(0, lambda: self._done(result))
        except Exception as e:
            err = traceback.format_exc()
            self.after(0, lambda: self._error(e, err))

    def _update_progress(self, cur, total, name, pct):
        self.progress.configure(value=pct)
        self.status_var.set(f"[{cur}/{total}] {name}")
        if cur == 1 or cur == total or cur % 20 == 0:
            self.log_write(f"[{cur}/{total}] {name}")

    def _done(self, r):
        self.start_btn.configure(state='normal')
        self.cancel_btn.configure(state='disabled')
        self.progress.configure(value=100)
        self.status_var.set(f"完成：写入 {r['written']} / {r['total']} 个文件")
        self.log_write(f"✅ 还原目标：{r['target']}")
        self.log_write(f"   参与解析的 md 文件：")
        for p in r['files_scanned']:
            self.log_write(f"   ├─ {p}")
        if r['errors']:
            for e in r['errors']:
                self.log_write(f"⚠ {e}")
        if r['skipped']:
            for s in r['skipped']:
                self.log_write(f"⚠ 跳过：{s}")
        messagebox.showinfo(
            "完成",
            f"还原完成！\n\n目标文件夹：\n{r['target']}\n\n"
            f"写入文件数：{r['written']} / {r['total']}\n"
            f"扫描 md 文件：{len(r['files_scanned'])} 个"
            + (f"\n跳过：{len(r['skipped'])} 项" if r['skipped'] else ""),
        )

    def _error(self, e, err):
        self.start_btn.configure(state='normal')
        self.cancel_btn.configure(state='disabled')
        self.status_var.set("发生错误")
        self.log_write(err)
        messagebox.showerror("错误", f"还原失败：{e}")

    def cancel(self):
        self.cancel_event.set()
        self.status_var.set("正在取消…")


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("文件夹 <-> Markdown 互转工具")
        root.geometry("760x660")
        root.minsize(660, 560)

        # 顶部工具条
        toolbar = ttk.Frame(root, padding=(12, 8, 12, 0))
        toolbar.pack(fill='x')
        ttk.Button(toolbar, text="生成 AI 规范文件（指导其他 AI 输出格式）",
                   command=self.save_ai_guide).pack(side='right')

        nb = ttk.Notebook(root)
        nb.pack(fill='both', expand=True, padx=8, pady=8)
        self.export_tab = ExportTab(nb)
        self.restore_tab = RestoreTab(nb)
        nb.add(self.export_tab, text="  导出（文件夹 → Markdown）  ")
        nb.add(self.restore_tab, text="  还原（Markdown → 文件夹）  ")

    def save_ai_guide(self):
        out = filedialog.asksaveasfilename(
            title="保存 AI 规范文件",
            defaultextension=".md",
            initialfile="AI输出规范_文件夹Markdown格式.md",
            filetypes=[("Markdown 文件", "*.md"), ("所有文件", "*.*")],
        )
        if not out:
            return
        try:
            Path(out).write_text(AI_GUIDE_MD, encoding='utf-8')
            messagebox.showinfo("完成",
                f"AI 规范文件已保存：\n{out}\n\n"
                "把它发给其他 AI，它们就能按格式输出可还原的 Markdown。")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{e}")


def main():
    root = tk.Tk()
    try:
        root.tk.call('tk', 'scaling', 1.2)
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()