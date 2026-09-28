#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件夹转 Markdown 导出工具
- 选择文件夹
- 生成 MD 文件：目录结构 + 文件/文件夹统计 + 每个文件的路径与内容（代码栏包裹）
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
    """根据文件名或扩展名推断代码块语言标识"""
    name_lower = fpath.name.lower()
    if name_lower in SPECIAL_FILES:
        return SPECIAL_FILES[name_lower]
    return EXT_LANG_MAP.get(fpath.suffix.lower(), '')


def is_binary_file(fpath: Path, blocksize: int = 8192) -> bool:
    """通过检测 NUL 字节判断是否二进制文件"""
    try:
        with open(fpath, 'rb') as f:
            chunk = f.read(blocksize)
        return b'\x00' in chunk if chunk else False
    except (OSError, PermissionError):
        return True


def read_text_file(fpath: Path):
    """尝试多种编码读取文本文件，返回 (内容, 使用的编码)"""
    raw = fpath.read_bytes()
    for enc in ('utf-8-sig', 'utf-8', 'gbk', 'big5', 'latin-1'):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', errors='replace'), 'utf-8(replace)'


def safe_fence(content: str) -> str:
    """根据内容里最长的连续反引号，返回足够长的代码围栏，避免冲突"""
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
    """深度优先遍历：每个目录内先子目录后文件，各自按名称排序"""
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
    """生成类似 tree 命令的目录结构文本"""
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
    """统计子文件夹总数（不含根目录本身）"""
    n = 0
    for _, dirnames, _ in os.walk(root):
        if not include_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        n += len(dirnames)
    return n


# ==================== 核心导出逻辑 ====================
def generate_markdown(
    root_dir: Path,
    out_path: Path,
    include_hidden: bool = False,
    max_size_mb: float = 10.0,
    progress_cb=None,
    cancel_event=None,
) -> dict:
    root_dir = Path(root_dir).resolve()
    out_path = Path(out_path).resolve()
    max_bytes = int(max_size_mb * 1024 * 1024) if max_size_mb > 0 else 0

    all_files = list(walk_sorted(root_dir, include_hidden))
    total = len(all_files)
    dir_count = count_dirs(root_dir, include_hidden)

    with open(out_path, 'w', encoding='utf-8', newline='\n') as fp:
        # ---------- 头部信息 ----------
        fp.write(f"# 文件夹内容导出：{root_dir.name}\n\n")
        fp.write(f"- **根目录**：`{root_dir}`\n")
        fp.write(f"- **导出时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        fp.write(f"- **文件总数**：{total}\n")
        fp.write(f"- **文件夹总数**：{dir_count}（不含根目录）\n")
        fp.write(f"- **包含隐藏项**：{'是' if include_hidden else '否'}\n")
        fp.write(f"- **单文件内容上限**：{'不限制' if max_bytes == 0 else f'{max_size_mb} MB'}\n\n")
        fp.write("---\n\n")

        # ---------- 目录结构 ----------
        fp.write("## 一、目录结构\n\n")
        fp.write("```\n")
        fp.write(generate_tree(root_dir, include_hidden))
        fp.write("\n```\n\n")
        fp.write("---\n\n")

        # ---------- 文件内容 ----------
        fp.write("## 二、文件内容\n\n")

        for idx, fpath in enumerate(all_files, 1):
            if cancel_event and cancel_event.is_set():
                fp.write("\n> ⚠️ 用户已取消导出，以下内容不完整。\n")
                break

            try:
                rel = fpath.relative_to(root_dir)
            except ValueError:
                rel = fpath
            try:
                size = fpath.stat().st_size
            except OSError:
                size = 0

            if progress_cb:
                progress_cb(idx, total, rel.as_posix())

            fp.write(f"### {idx}. `{rel.as_posix()}`\n\n")
            fp.write(f"- 文件名：`{fpath.name}`\n")
            fp.write(f"- 相对路径：`{rel.as_posix()}`\n")
            fp.write(f"- 绝对路径：`{fpath}`\n")
            fp.write(f"- 文件大小：{human_size(size)}\n\n")

            # 二进制 / 超限 直接跳过内容
            if is_binary_file(fpath):
                fp.write("> 二进制文件，未导出内容。\n\n---\n\n")
                continue
            if max_bytes and size > max_bytes:
                fp.write(f"> 文件过大（{human_size(size)}），超过上限，未导出内容。\n\n---\n\n")
                continue

            try:
                content, enc = read_text_file(fpath)
            except Exception as e:
                fp.write(f"> 读取失败：`{e}`\n\n---\n\n")
                continue

            lang = get_language(fpath)
            fence = safe_fence(content)
            fp.write(f"<!-- 文件编码：{enc} -->\n\n")
            fp.write(f"{fence}{lang}\n")
            fp.write(content)
            if not content.endswith('\n'):
                fp.write('\n')
            fp.write(f"{fence}\n\n---\n\n")

    return {'files': total, 'dirs': dir_count, 'output': str(out_path)}


# ==================== GUI ====================
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("文件夹转 Markdown 导出工具")
        root.geometry("660x520")
        root.minsize(560, 440)

        self.folder_var = tk.StringVar()
        self.include_hidden_var = tk.BooleanVar(value=False)
        self.max_size_var = tk.StringVar(value="10")
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
        size_row = ttk.Frame(opts)
        size_row.pack(fill='x', pady=(8, 0))
        ttk.Label(size_row, text="单文件内容大小上限（MB，0 = 不限制）：").pack(side='left')
        ttk.Entry(size_row, textvariable=self.max_size_var, width=8).pack(side='left', padx=6)

        # 按钮
        btn_row = ttk.Frame(main)
        btn_row.pack(fill='x', pady=6)
        self.start_btn = ttk.Button(btn_row, text="开始导出", command=self.start_export)
        self.start_btn.pack(side='left')
        self.cancel_btn = ttk.Button(
            btn_row, text="取消", command=self.cancel_export, state='disabled')
        self.cancel_btn.pack(side='left', padx=6)

        # 进度
        prog = ttk.LabelFrame(main, text="进度", padding=10)
        prog.pack(fill='both', expand=True, pady=6)
        self.progress = ttk.Progressbar(prog, mode='determinate')
        self.progress.pack(fill='x')
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(prog, textvariable=self.status_var,
                  wraplength=580, justify='left').pack(fill='x', pady=(8, 0))

        log_frame = ttk.Frame(prog)
        log_frame.pack(fill='both', expand=True, pady=(8, 0))
        self.log = tk.Text(log_frame, height=8, wrap='none')
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
            max_mb = float(self.max_size_var.get().strip() or "0")
            if max_mb < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "大小上限必须是 ≥ 0 的数字。")
            return

        out_path = filedialog.asksaveasfilename(
            title="保存 Markdown 文件",
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
                  self.include_hidden_var.get(), max_mb),
            daemon=True,
        )
        self.worker.start()

    def _worker(self, root_path: Path, out_path: Path,
                include_hidden: bool, max_mb: float):
        try:
            counter = {'last': 0}

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
        # 日志不刷太频
        if cur == 1 or cur == total or cur % 20 == 0:
            self.log_write(f"[{cur}/{total}] {name}")

    def _on_done(self, result):
        self.start_btn.configure(state='normal')
        self.cancel_btn.configure(state='disabled')
        self.progress.configure(value=100)
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
        # 让高 DPI 屏幕上字体清晰一点
        root.tk.call('tk', 'scaling', 1.2)
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()