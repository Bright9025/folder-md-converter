# Folder Markdown Format Specification (for AI Reference)

This document specifies a Markdown format that fully describes the contents
of a folder. Any AI that follows this specification can produce output that
users can feed into the "Folder <-> Markdown Converter" restore function to
recreate the real folder structure and file contents.

---

## 1. Overall Structure

The Markdown contains three sections in order, separated by `---`:

```
# Title and Metadata

## 1. Tree
(code block containing a directory tree)

## 2. Contents
### 1. `path/to/file1`
(metadata + content)

### 2. `path/to/file2`
(metadata + content)
```

---

## 2. Title and Metadata

The file starts with a level-1 heading followed by a metadata list:

```markdown
# myproject

- root: `/Users/me/myproject`
- exported: 2026-01-01 12:00:00
- files: 5
- folders: 2
- include_hidden: False
- max_file_mb: 10.0
- split_mb: 0
```

The restore process relies on each file block's path, not on the header.
Header metadata is for human readers.

---

## 3. Tree (Recommended, Not Required)

Under `## 1. Tree`, place a code block containing a `tree`-like directory
structure. **The restore function does not rely on this section**, but it is
recommended for readability.

```text
myproject/
├── src/
│   ├── main.py
│   └── utils.py
└── README.md
```

---

## 4. File Content Blocks (Core)

Under `## 2. Contents`, each file is represented by one block:

### 4.1 Block Header (Mandatory)

```markdown
### N. `relative/path`
```

- `N` starts at 1 and increments globally.
- The path inside backticks is **relative to the root folder**, using `/`.
- The path must not be absolute and must not contain `..`.

### 4.2 Metadata (Optional)

```markdown
- name: `main.py`
- rel: `src/main.py`
- abs: `/Users/me/myproject/src/main.py`
- size: 1.23 KB
```

**Only the `### N. \`path\`` line is mandatory.** The restore process reads
that line and the code block beneath it.

### 4.3 Encoding Marker (Optional)

If the file is not UTF-8, add an HTML comment:

```markdown
<!-- encoding: gbk -->
```

The Chinese form `<!-- 文件编码：gbk -->` is also accepted.

### 4.4 Content (Mandatory)

Wrap content in a **code fence** with at least 3 backticks:

````markdown
```python
print("hello")
```
````

The language tag (`python`, `js`, etc.) is optional and ignored by the
restore process.
**If the file content itself contains runs of backticks, the fence must be
longer than the longest run.** For example, if the content has at most 3
consecutive backticks, use at least 4 for the fence.

### 4.5 Block Separator (Recommended)

End each file block with a line containing `---`:

```markdown
### 1. `README.md`

- name: `README.md`

```text
hello
```

---
```

---

## 5. Binary and Oversized Files

If a file is binary or too large, output a note instead of content:

```markdown
### 3. `logo.png`

- name: `logo.png`
- size: 12.34 KB

> binary file, no content exported.

---
```

During restore, such files are created as empty placeholders.

---

## 6. Complete Example

````markdown
# demo

- root: `/tmp/demo`
- exported: 2026-01-01 12:00:00
- files: 2
- folders: 1
- include_hidden: False
- max_file_mb: 10.0
- split_mb: 0

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
- abs: `/tmp/demo/README.md`
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
- abs: `/tmp/demo/src/main.py`
- size: 20 B

<!-- encoding: utf-8 -->

```python
print("hello world")
```

---
````

---

## 7. AI Output Checklist

- [ ] Top-level level-1 heading `# ...`
- [ ] Contains a `## 2. Contents` section (or Chinese equivalent)
- [ ] Each file starts with `### N. \`relative/path\``
- [ ] `N` increments from 1 without gaps
- [ ] Paths use forward slashes `/`, are not absolute, contain no `..`
- [ ] Content is wrapped in a code fence (at least 3 backticks)
- [ ] If the content contains backticks, the fence must be longer
- [ ] Binary / oversized files use `> note` instead of content
- [ ] Blocks are separated by `---`
- [ ] **Do not wrap the entire document in a code block**

---

## 8. Common Mistakes

| Mistake | Consequence | Fix |
|---|---|---|
| Missing `### N. \`path\`` | File will not be restored | Add the block header |
| Absolute path | Rejected or path escape | Use a relative path |
| Fence too short | Content is truncated | Use a longer fence |
| Whole md wrapped in ``` | Cannot be parsed | Do not wrap the entire document |
| No `---` between blocks | Usually fine, but less readable | Add `---` |
| Path contains `..` | Rejected and skipped | Use a normal relative path |

---

## 9. Split Output (Optional)

For very long content, split into one mother file and several parts:

- **Mother file**: contains metadata, tree, and an index table:

  ```markdown
  | Part | Range | Count | Link |
  |:---|:---|---:|:---|
  | `xxx_part01.md` | 1 - 120 | 120 | [Open](./xxx_part01.md) |
  ```

- **Part files**: named `<mother_name>_partNN.md`, containing several
  `### N. \`path\`` blocks (numbering is globally continuous).
  The restore tool will auto-discover and merge all parts.
