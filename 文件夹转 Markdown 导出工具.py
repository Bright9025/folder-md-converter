#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件夹转 Markdown 导出工具（支持自动拆分）
- 选择文件夹 → 生成 Markdown
- 内容超过拆分阈值 → 生成母文件 + 若干子文件
"""

import os
import threading
import traceback
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ==================== 扩展名 -> 代码语言映射 ====================
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
    'dockerfile': 'dockerfile',
    'makefile': 'makefile',
    'gnumakefile': 'makefile',
    'cmakelists.txt': 'cmake',
    '.gitignore': 'gitignore',
    '.gitattributes': 'gitignore',
    '.env': 'bash',
    '.editorconfig': 'ini',
    '.npmrc': 'ini',
    'go.mod': 'go',
    'cargo.toml': 'toml',
    'cargo.lock': 'toml',
}


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


# ==================== 内容块生成 ====================
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
    lines = []
    lines.append(f"### {idx}. `{rel.as_posix()}`\n\n")
    lines.append(f"- 文件名：`{fpath.name}`\n")
    lines.append(f"- 相对路径：`{rel.as_posix()}`\n")
    lines.append(f"- 绝对路径：`{fpath}`\n")
    lines.append(f"- 文件大小：{human_size(size)}\n\n")

    if binary:
        lines.append("> 二进制文件，未导出内容。\n\n---\n\n")
        return "".join(lines)
    if max_bytes and size > max_bytes:
        lines.append(f"> 文件过大（{human_size(size)}），超过上限，未导出内容。\n\n---\n\n")
        return "".join(lines)

    try:
        content, enc = read_text_file(fpath)
    except Exception as e:
        lines.append(f"> 读取失败：`{e}`\n\n---\n\n")
        return "".join(lines)

    lang = get_language(fpath)
    fence = safe_fence(content)
    lines.append(f"<!-- 文件编码：{enc} -->\n\n")
    lines.append(f"{fence}{lang}\n")
    lines.append(content)
    if not content.endswith('\n'):
        lines.append('\n')
    lines.append(f"{fence}\n\n---\n\n")
    return "".join(lines)


# ==================== 核心导出 ====================
def generate_markdown(
    root_dir: Path,
    out_path: Path,
    include_hidden: bool = False,
    max_size_mb: float = 10.0,
    split_size_mb: float = 0.0,
    progress_cb=None,
    cancel_event=None,
) -> dict:
    root_dir = Path(root_dir).resolve()
    out_path = Path(out_path).resolve()
    max_bytes = int(max_size_mb * 1024 * 1024) if max_size_mb > 0 else 0
    split_bytes = int(split_size_mb * 1024 * 1024) if split_size_mb > 0 else 0

    all_files = list(walk_sorted(root_dir, include_hidden))
    total = len(all_files)
    dir_count = count_dirs(root_dir, include_hidden)

    # ---- 收集每个文件的元信息与内容块大小估算 ----
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
        if binary or (max_bytes and size > max_bytes):
            content_size = 260
        else:
            content_size = size + 420  # 元数据 + 围栏
        file_info.append({
            'path': fpath, 'rel': rel, 'size': size,
            'binary': binary, 'content_size': content_size,
        })

    tree_text = generate_tree(root_dir, include_hidden)
    header_text = _build_header(root_dir, total, dir_count,
                                include_hidden, max_size_mb, split_size_mb)
    header_size = len((header_text + tree_text).encode('utf-8')) + 4000

    total_content_size = sum(fi['content_size'] for fi in file_info)

    # ---- 判断是否需要拆分 ----
    if split_bytes <= 0 or (header_size + total_content_size) <= split_bytes:
        need_split = False
    else:
        need_split = True

    base_dir = out_path.parent
    base_name = out_path.stem
    parts_written = []
    part_meta = []

    # ========== 情况 A：不拆分，单文件输出 ==========
    if not need_split:
        with open(out_path, 'w', encoding='utf-8', newline='\n') as fp:
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
        return {
            'files': total, 'dirs': dir_count,
            'output': str(out_path), 'parts': [], 'split': False,
        }

    # ========== 情况 B：拆分 ==========
    # 规划每个子文件包含的文件范围
    part_header_reserve = 400
    chunks = []
    cur_start = 0
    cur_size = part_header_reserve
    for i, fi in enumerate(file_info):
        bs = fi['content_size']
        if i > cur_start and (cur_size + bs) > split_bytes:
            chunks.append((cur_start, i))
            cur_start = i
            cur_size = part_header_reserve
        cur_size += bs
    if cur_start < len(file_info):
        chunks.append((cur_start, len(file_info)))

    # 只有 1 块就不用拆了（回到单文件模式）
    if len(chunks) <= 1:
        with open(out_path, 'w', encoding='utf-8', newline='\n') as fp:
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
        return {
            'files': total, 'dirs': dir_count,
            'output': str(out_path), 'parts': [], 'split': False,
        }

    n_parts = len(chunks)
    width = max(2, len(str(n_parts)))

    # ---- 写子文件 ----
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
            'name': part_name,
            'start': start + 1,
            'end': end,
            'count': len(part_files),
        })

    # ---- 写母文件 ----
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
        fp.write("\n> 提示：本母文件包含目录结构与索引，具体文件内容请点击上表链接查看。\n")

    return {
        'files': total, 'dirs': dir_count,
        'output': str(out_path),
        'parts': [str(p) for p in parts_written],
        'split': True,
    }


# ==================== GUI ====================
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("文件夹转 Markdown 导出工具（支持拆分）")
        root.geometry("700x580")
        root.minsize(600, 500)

        self.folder_var = tk.StringVar()
        self.include_hidden_var = tk.BooleanVar(value=False)
        self.max_size_var = tk.StringVar(value="10")
        self.split_size_var = tk.StringVar(value="5")
        self.cancel_event = threading.Event()
        self.worker = None

        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=14)
        main.pack(fill='both', expand=True)

        # 选择文件夹
        row = ttk.Frame(main)
        row.pack(fill='x', pady=6)
        ttk.Label(row, text="目标文件夹：").pack(side='left')
        ttk.Entry(row, textvariable=self.folder_var).pack(
            side='left', fill='x', expand=True, padx=6)
        ttk.Button(row, text="选择…", command=self.choose_folder).pack(side='left')

        # 选项
        opts = ttk.LabelFrame(main, text="选项", padding=10)
        opts.pack(fill='x', pady=6)

        ttk.Checkbutton(
            opts,
            text="包含隐藏文件 / 文件夹（以 . 开头）",
            variable=self.include_hidden_var,
        ).pack(anchor='w')

        r1 = ttk.Frame(opts)
        r1.pack(fill='x', pady=(8, 0))
        ttk.Label(r1, text="单文件内容大小上限（MB，0 = 不限制）：").pack(side='left')
        ttk.Entry(r1, textvariable=self.max_size_var, width=8).pack(side='left', padx=6)

        r2 = ttk.Frame(opts)
        r2.pack(fill='x', pady=(6, 0))
        ttk.Label(r2, text="拆分阈值（MB，0 = 不拆分）：").pack(side='left')
        ttk.Entry(r2, textvariable=self.split_size_var, width=8).pack(side='left', padx=6)
        ttk.Label(
            r2,
            text="超过阈值时生成母文件 + 若干子文件",
            foreground="#666",
        ).pack(side='left', padx=6)

        # 按钮
        btn_row = ttk.Frame(main)
        btn_row.pack(fill='x', pady=6)
        self.start_btn = ttk.Button(btn_row, text="开始导出", command=self.start_export)
        self.start_btn.pack(side='left')
        self.cancel_btn = ttk.Button(
            btn_row, text="取消", command=self.cancel_export, state='disabled')
        self.cancel_btn.pack(side='left', padx=6)

        # 进度 + 日志
        prog = ttk.LabelFrame(main, text="进度", padding=10)
        prog.pack(fill='both', expand=True, pady=6)
        self.progress = ttk.Progressbar(prog, mode='determinate')
        self.progress.pack(fill='x')
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(prog, textvariable=self.status_var,
                  wraplength=620, justify='left').pack(fill='x', pady=(8, 0))

        log_frame = ttk.Frame(prog)
        log_frame.pack(fill='both', expand=True, pady=(8, 0))
        self.log = tk.Text(log_frame, height=10, wrap='none')
        self.log.pack(side='left', fill='both', expand=True)
        sb = ttk.Scrollbar(log_frame, command=self.log.yview)
        sb.pack(side='right', fill='y')
        self.log.configure(yscrollcommand=sb.set, state='disabled')

    # ---------- 交互 ----------
    def choose_folder(self):
        path = filedialog.askdirectory(title="选择要导出的文件夹")
        if path:
            self.folder_var.set(path)

    def log_write(self, msg: str):
        self.log.configure(state='normal')
        self.log.insert('end', msg + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def _parse_float(self, s: str, default=0.0):
        s = s.strip()
        if not s:
            return default
        v = float(s)
        if v < 0:
            raise ValueError
        return v

    def start_export(self):
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("提示", "请先选择目标文件夹。")
            return
        root_path = Path(folder)
        if not root_path.is_dir():
            messagebox.showerror("错误", "所选路径不是有效文件夹。")
            return

        try:
            max_mb = self._parse_float(self.max_size_var.get(), 10.0)
            split_mb = self._parse_float(self.split_size_var.get(), 0.0)
        except ValueError:
            messagebox.showerror("错误", "大小参数必须是 ≥ 0 的数字。")
            return

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
        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')
        self.cancel_event.clear()

        self.worker = threading.Thread(
            target=self._worker,
            args=(root_path, Path(out_path),
                  self.include_hidden_var.get(), max_mb, split_mb),
            daemon=True,
        )
        self.worker.start()

    def _worker(self, root_path: Path, out_path: Path,
                include_hidden: bool, max_mb: float, split_mb: float):
        try:
            def progress_cb(cur, total, name):
                step = max(1, total // 200) if total > 200 else 1
                if cur % step != 0 and cur != total:
                    return
                pct = (cur / total * 100) if total else 100.0
                self.root.after(0, lambda: self._update_progress(cur, total, name, pct))

            result = generate_markdown(
                root_path, out_path,
                include_hidden=include_hidden,
                max_size_mb=max_mb,
                split_size_mb=split_mb,
                progress_cb=progress_cb,
                cancel_event=self.cancel_event,
            )
            self.root.after(0, lambda: self._on_done(result))
        except Exception as e:
            err = traceback.format_exc()
            self.root.after(0, lambda: self._on_error(e, err))

    def _update_progress(self, cur, total, name, pct):
        self.progress.configure(value=pct)
        self.status_var.set(f"[{cur}/{total}] {name}")
        if cur == 1 or cur == total or cur % 20 == 0:
            self.log_write(f"[{cur}/{total}] {name}")

    def _on_done(self, result):
        self.start_btn.configure(state='normal')
        self.cancel_btn.configure(state='disabled')
        self.progress.configure(value=100)
        if result['split']:
            self.status_var.set(
                f"完成：{result['files']} 个文件 / {result['dirs']} 个文件夹，"
                f"已拆分为 {len(result['parts'])} 个子文件")
            self.log_write(f"✅ 母文件：{result['output']}")
            for p in result['parts']:
                self.log_write(f"   ├─ {p}")
            messagebox.showinfo(
                "完成",
                f"导出完成（已拆分）！\n\n"
                f"文件数：{result['files']}\n"
                f"文件夹数：{result['dirs']}\n"
                f"子文件数：{len(result['parts'])}\n\n"
                f"母文件：\n{result['output']}",
            )
        else:
            self.status_var.set(
                f"完成：{result['files']} 个文件，{result['dirs']} 个文件夹")
            self.log_write(f"✅ 已导出到：{result['output']}")
            messagebox.showinfo(
                "完成",
                f"导出完成！\n\n"
                f"文件数：{result['files']}\n"
                f"文件夹数：{result['dirs']}\n\n"
                f"输出文件：\n{result['output']}",
            )

    def _on_error(self, e, err):
        self.start_btn.configure(state='normal')
        self.cancel_btn.configure(state='disabled')
        self.status_var.set("发生错误")
        self.log_write(err)
        messagebox.showerror("错误", f"导出失败：{e}")

    def cancel_export(self):
        self.cancel_event.set()
        self.status_var.set("正在取消…")


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