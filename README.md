# Parsnips

Generate, search, and cite SWHIDs for Python code fragments like classes, functions, and expressions.

## Overview

**Parsnips** is a Python tool that analyzes source files to create a citable hierarchy of folders and metadata files representing nodes in a parsed abstract syntax tree (AST). AST nodes correspond to meaningful code fragments such as classes, functions, and expressions. 

The metadata files and folders can be stored in your repository. If your repository is archived on Software Heritage, you can retrieve and cite the SWHIDs for these fragments. This tool allows you to search for SWHIDs, including the qualified SWHIDs archived on Software Heritage. 

Parsnips uses the built-in `ast` module and `asttokens` to generate reproducible identifiers (SWHIDs) for:

- Functions
- Classes
- Assignments
- Expressions
- Other AST nodes

Each node is represented by a metadata file stored inside a `.parsnips/` directory.

## Extraction Protocol

### 1. Directory vs. File Input

- When run on a **directory**, Parsnips creates a unified `.parsnips/` directory in the root and recursively processes all `.py` files.
- When run on a **file**, it creates a `.parsnips/` folder adjacent to the file and processes only that file.

### 2. Directory Traversal

- Traverses all subdirectories unless ignored by `.parsnipsignore`.
- Skips `.parsnips` folders to avoid processing output.
- Uses `pathspec` to match ignore rules from `.parsnipsignore`.

### 3. File and Node Handling

- Parses the AST using `ast` and `asttokens`.
- Computes the file-level SWHID.
- Recursively walks each AST node and extracts its:
  - type (e.g., `FunctionDef`)
  - label (e.g., name or identifier)
  - source text
  - line and column info

### 4. Output Folder Structure

- Each processed file results in a folder:
  ```
  .parsnips/pdir_<subdir>/.../pfile_<filename>_<ext>/
  ```
- Each AST node has a folder:
  ```
  EL<lineno>C<col_offset>T<traversal_index>__<node_type>/
  ```

### 5. Outputs per Node

Each node folder contains:

- `node_metadata.json` which contains the following structured metadata:
  - `type`: AST node type
  - `label`: Identifier or name (e.g., function name)
  - `text`: Exact source text of the node
  - `lineno`: Declared line number (or null)
  - `effective_lineno`: Inherited line number
  - `col_offset`: Column offset
  - `file_swhid`: SWHID for the source file
  - `source_path`: Path relative to repo root
  - `source_filename`: Original filename

## Fragment-Level SWHIDs

The `node_metadata.json` file is the fragment boundary. Its SWHID is the `blake2s()` hash over its full serialized content. This includes both structure and source content.

This makes SWHIDs semantically meaningful and reproducible.

## Searching for Qualified SWHIDs and Citing Fragments

You can search for SWHIDs by source code using:

- `-s {literal text in source code}`
- `-s -r {regular expression for text in source code}`

You can attach SWHID context qualifiers using:

- `--repo-url`
- `--commit`, `--release-name`, or `--ref-name`

Parsnips can compute:

- `node_swhid_without_qualifiers`: SWHID of `node_metadata.json` without context qualifiers
- `node_swhid_with_qualifiers`: SWHID of `node_metadata.json` with anchor and path qualifiers

## Ignoring Files and Folders

Parsnips supports a `.parsnipsignore` file using `.gitignore`-style rules.

Example:
```
tests/
**/__pycache__/
ignore_this.py
```

## CLI Parameters

| Argument | Description |
|----------|-------------|
| `path` (positional) | Path to file or directory (default: current directory) |
| `-c`, `--clean` | Delete the `.parsnips` folder |
| `-s`, `--search` | Regular expression to search within node texts |
| `-u`, `--unicode` | Normalize search pattern and source code (Unicode NFC) |
| `-r`, `--regex` | Interpret the search string as a regular expression |
| `-q`, `--quiet` | Suppress logs to stdout |
| `-l`, `--logfile` | Write logs to specified JSON file |
| `--strict` | Abort on first error or missing `.parsnips` folder |
| `--repo-url` | Repository origin URL (for qualified SWHID generation) |
| `--commit` | Commit SHA (if known) |
| `--release-name` | Release name (annotated tag) |
| `--ref-name` | Branch or lightweight tag |
| `--repo-root` | Path to the root of the local repo (default: cwd) |

## Example Usage

Extract:
```bash
parsnips my_project/
```

Search:
```bash
parsnips my_project/ --search "def hello_world"
```

### Example Search Output

#### 1. Basic Search Without Repository Context

Suppose you have the following `my_project/src/hello_world.py` file:
```python

# my first function
def hello_world():
  print("hello world")

hello_world()

# my first class
class HelloWorld:
  def __init__(self, msg):
    self.msg = msg
  
  def print(self):
    print(self.msg)

h = HelloWorld(msg="Hello World!")
h.print()


```

If you run:

```bash
parsnips my_project/ --search "def hello_world"
```

or 
```bash
cd my_project
parsnips --search "def hello_world"
```

You should see output like:

```json
{
  ".parsnips/pdir_src/pfile_hello_world_py/EL0C0T1__Module/EL1C0T2__FunctionDef/node_metadata.json": {
    "node_metadata": {
      "col_offset": 0,
      "effective_lineno": 1,
      "file_swhid": "swh:1:cnt:beb39a0824cd8504eefa2547d55db6c80c07ab35344656e355418da04902aff9",
      "label": "hello_world",
      "lineno": 1,
      "source_filename": "hello_world.py",
      "source_path": "src/hello_world.py",
      "text": "def hello_world():\n  print(\"hello world\")",
      "type": "FunctionDef"
    },
    "node_swhid_with_qualifiers": null,
    "node_swhid_without_qualifiers": "swh:1:cnt:461e590204211379f783d56f790f596c5352e26df74e8c566677054c66005a94",
    "search_regex_match_groups": null,
    "search_text": "def hello_world",
    "search_used_regex": false,
    "search_used_unicode": false
  },
  ".parsnips/pdir_src/pfile_hello_world_py/EL0C0T1__Module/node_metadata.json": {
    "node_metadata": {
      "col_offset": 0,
      "effective_lineno": 0,
      "file_swhid": "swh:1:cnt:beb39a0824cd8504eefa2547d55db6c80c07ab35344656e355418da04902aff9",
      "label": "node",
      "lineno": null,
      "source_filename": "hello_world.py",
      "source_path": "src/hello_world.py",
      "text": "def hello_world():\n  print(\"hello world\")\n\nhello_world()\n\n# my first class\nclass HelloWorld:\n  def __init__(self, msg):\n    self.msg = msg\n  \n  def print(self):\n    print(self.msg)\n\nh = HelloWorld(msg=\"Hello World!\")\nh.print()",
      "type": "Module"
    },
    "node_swhid_with_qualifiers": null,
    "node_swhid_without_qualifiers": "swh:1:cnt:f059936a0c56e2f5adc01f3f64d12017ab3f44b07c7d74a9c78815ec9a43229d",
    "search_regex_match_groups": null,
    "search_text": "def hello_world",
    "search_used_regex": false,
    "search_used_unicode": false
  }
}
```

#### 2. Search With Repository Context

If you run:

```bash
parsnips my_project/ --search "def hello_world" \
  --repo-url https://github.com/example/repo \
  --commit a1b2c3d4e5
```

You might see output like:

```json
{
  ".parsnips/pdir_src/pfile_hello_world_py/EL0C0T1__Module/EL1C0T2__FunctionDef/node_metadata.json": {
    "node_metadata": {
      "col_offset": 0,
      "effective_lineno": 1,
      "file_swhid": "swh:1:cnt:beb39a0824cd8504eefa2547d55db6c80c07ab35344656e355418da04902aff9",
      "label": "hello_world",
      "lineno": 1,
      "source_filename": "hello_world.py",
      "source_path": "src/hello_world.py",
      "text": "def hello_world():\n  print(\"hello world\")",
      "type": "FunctionDef"
    },
    "node_swhid_without_qualifiers": "swh:1:cnt:a9c3f8e9dabb93c0f89c3e9278d1f3b29b60f7d8e624fcf8f1764a2b3a2fc213",
    "node_swhid_with_qualifiers": "swh:1:cnt:a9c3f8e9dabb93c0f89c3e9278d1f3b29b60f7d8e624fcf8f1764a2b3a2fc213;origin=https://github.com/example/repo;anchor=swh:1:rev:a1b2c3d4e5;path=/src/hello.py",
    "search_pattern": "def hello_world",
    "search_regex_match_groups": null,
    "search_used_regex": false,
    "search_used_unicode": false
  },
  ".parsnips/pdir_src/pfile_hello_world_py/EL0C0T1__Module/node_metadata.json": {
    "node_metadata": {
      "col_offset": 0,
      "effective_lineno": 0,
      "file_swhid": "swh:1:cnt:beb39a0824cd8504eefa2547d55db6c80c07ab35344656e355418da04902aff9",
      "label": "node",
      "lineno": null,
      "source_filename": "hello_world.py",
      "source_path": "src/hello_world.py",
      "text": "def hello_world():\n  print(\"hello world\")\n\nhello_world()\n\n# my first class\nclass HelloWorld:\n  def __init__(self, msg):\n    self.msg = msg\n  \n  def print(self):\n    print(self.msg)\n\nh = HelloWorld(msg=\"Hello World!\")\nh.print()",
      "type": "Module"
    },
    "node_swhid_without_qualifiers": "swh:1:cnt:f2ae6724c3a37e63cfed7ff3eae8a7f835f11f8be9f9f70b8dc67cc313a9cb11",
    "node_swhid_with_qualifiers": "swh:1:cnt:f2ae6724c3a37e63cfed7ff3eae8a7f835f11f8be9f9f70b8dc67cc313a9cb11;origin=https://github.com/example/repo;anchor=swh:1:rev:a1b2c3d4e5;path=/src/hello.py",
    "search_pattern": "def hello_world",
    "search_regex_match_groups": null,
    "search_used_regex": false,
    "search_used_unicode": false
  }
}
```

#### 3. Search With Repository Context AND Regular Expression with Group Name

If you run:

```bash
parsnips my_project/ --search "def (?P<funcname>hello\\w+)" \
  --repo-url https://github.com/example/repo \
  --commit a1b2c3d4e5
```

You might see output like:

```json
{
  ".parsnips/pdir_src/pfile_hello_world_py/EL0C0T1__Module/EL1C0T2__FunctionDef/node_metadata.json": {
    "node_metadata": {
      "col_offset": 0,
      "effective_lineno": 1,
      "file_swhid": "swh:1:cnt:beb39a0824cd8504eefa2547d55db6c80c07ab35344656e355418da04902aff9",
      "label": "hello_world",
      "lineno": 1,
      "source_filename": "hello_world.py",
      "source_path": "src/hello_world.py",
      "text": "def hello_world():\n  print(\"hello world\")",
      "type": "FunctionDef"
    },
    "node_swhid_without_qualifiers": "swh:1:cnt:a9c3f8e9dabb93c0f89c3e9278d1f3b29b60f7d8e624fcf8f1764a2b3a2fc213",
    "node_swhid_with_qualifiers": "swh:1:cnt:a9c3f8e9dabb93c0f89c3e9278d1f3b29b60f7d8e624fcf8f1764a2b3a2fc213;origin=https://github.com/example/repo;anchor=swh:1:rev:a1b2c3d4e5;path=/src/hello.py",
    "search_regex_match_groups": {
      "funcname": "hello_world"
    },
    "search_text": "def (?P<funcname>hello\\w+)",
    "search_used_regex": true,
    "search_used_unicode": false
  },
  ".parsnips/pdir_src/pfile_hello_world_py/EL0C0T1__Module/node_metadata.json": {
    "node_metadata": {
      "col_offset": 0,
      "effective_lineno": 0,
      "file_swhid": "swh:1:cnt:beb39a0824cd8504eefa2547d55db6c80c07ab35344656e355418da04902aff9",
      "label": "node",
      "lineno": null,
      "source_filename": "hello_world.py",
      "source_path": "src/hello_world.py",
      "text": "def hello_world():\n  print(\"hello world\")\n\nhello_world()\n\n# my first class\nclass HelloWorld:\n  def __init__(self, msg):\n    self.msg = msg\n  \n  def print(self):\n    print(self.msg)\n\nh = HelloWorld(msg=\"Hello World!\")\nh.print()",
      "type": "Module"
    },
    "node_swhid_without_qualifiers": "swh:1:cnt:f2ae6724c3a37e63cfed7ff3eae8a7f835f11f8be9f9f70b8dc67cc313a9cb11",
    "node_swhid_with_qualifiers": "swh:1:cnt:f2ae6724c3a37e63cfed7ff3eae8a7f835f11f8be9f9f70b8dc67cc313a9cb11;origin=https://github.com/example/repo;anchor=swh:1:rev:a1b2c3d4e5;path=/src/hello.py",
    "search_regex_match_groups": {
      "funcname": "hello_world"
    },
    "search_text": "def (?P<funcname>hello\\w+)",
    "search_used_regex": true,
    "search_used_unicode": false
  }
}
```

**Note** If run with `--strict` mode and a `.parsnips` folder is missing, the command will fail instead of silently returning empty results.

Clean:
```
parsnips my_project/ --clean
```

## Licensing

Parsnips is licensed under the **Apache License 2.0**.

### SPDX Identifier

```
Apache-2.0
```

## Citation

If you use Parsnips in your research or projects, please cite it using the metadata provided in [`CITATION.cff`](./CITATION.cff).

## Author

- Will Riley — [wanderingwill@gmail.com](mailto\:wanderingwill@gmail.com)

## Related Projects

- [Software Heritage](https://www.softwareheritage.org/)
- [SWHIDs specification](https://docs.softwareheritage.org/devel/swh-model/#swh-ids)

## Disclaimer

Parsnips is an experimental tool designed to support research and archival workflows. Use at your own risk. Feedback and contributions are welcome.