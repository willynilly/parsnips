# Parsnips

Generate, search, and cite SWHIDs for code fragments (functions, classes, expressions) using configurable extractors like Tree-sitter and LibCST. Parsnips enables reproducible citation of specific source code fragments and supports search, filtering, and SWHID qualifier resolution.

---

## Overview

**Parsnips** analyzes source code and produces a `parsnips.json` file containing a structured list of code fragments. Each fragment is assigned a reproducible SWHID and includes source range metadata and dependencies. Parsnips supports:

* Custom extractors (`tree-sitter`, `libcst`, etc.)
* Search using literal text, regex, or source regions
* Optional resolution of Software Heritage SWHID context qualifiers (origin, commit, release, etc.)
* JSON output for integration in reproducible research, documentation, and archival workflows

The `parsnips.json` and `parsnips-config.json` files should be committed to the root of your repository. This allows reproducible extraction and referencing by others. If your repository is archived by [Software Heritage](https://www.softwareheritage.org/), Parsnips can dynamically query the archive to locate the appropriate snapshot and anchor SWHIDs for citation.

You can submit your repository to Software Heritage using:

* [https://save.softwareheritage.org/](https://save.softwareheritage.org/)

Once archived, Parsnips can resolve qualified SWHIDs to specific nodes in your code.

> **Important:** You must run an **extraction** before you can perform a **search**. Extraction generates the `parsnips.json` file that is required for searching.

---

## Key Features

* Fragment extraction by syntax trees (Tree-sitter or LibCST)
* CLI and config-driven execution
* Supports repo-root detection for SWHID qualification
* JSON output with precise byte and line range metadata
* Search by code content or structured source region (line/column bounds)
* Dynamic anchor resolution from the Software Heritage archive

---

## Example Workflow

### Extract Fragments from a Python Project

```bash
parsnips --language python --include '**/*.py'
```

This creates two files in the **root of your repository**:

* `parsnips.json` — structured list of extracted fragments
* `parsnips-config.json` — config for reproducibility

You should add both files to version control.

### Search Fragments by Code Text

```bash
parsnips --search "def hello_world"
```

### Search with Regex and SWH Qualifiers

```bash
parsnips \
  --search "def (?P<funcname>hello_\\w+)" \
  --regex \
  --repo-url https://github.com/example/repo \
  --commit abc1234
```

### Search by Source Region

You can search all fragments **within a specific region** of a file using line and column bounds:

```bash
parsnips \
  --search "" \
  --start-line-number 10 \
  --start-col-offset 0 \
  --end-line-number 20 \
  --end-col-offset 100
```

This returns all semantic fragments (e.g. functions, classes, expressions) that fall **within** the specified region.

---

## Output Format

### Fragment JSON Structure

Each code fragment is described by:

```json
{
  "fragment_id": "src/main.py::3",
  "depends_on_fragment_ids": ["src/main.py::1"],
  "node_type": "FunctionDef",
  "text": "def my_func():\n  pass",
  "start_line_number": 10,
  "end_line_number": 11,
  "start_col_offset": 0,
  "end_col_offset": 6,
  "start_byte": 25,
  "end_byte": 45,
  "swhid": "swh:1:cnt:abc123...;bytes=25-45",
  "source_path": "src/main.py"
}
```

* `swhid` is a content-based identifier (hash over bytes) with byte range
* It is **unqualified** and always reproducible from the fragment contents

---

## SWHID Fragment Model

Each fragment’s `swhid` is computed as:

```
swh:1:cnt:<hash>;bytes=<start_byte>-<end_byte>
```

### Qualified vs. Unqualified SWHID

* The `swhid` inside a fragment is the content SWHID: it's computed only from the local file and byte range.
* When performing a **search**, Parsnips can attach context qualifiers to the node's SWHID:

```json
"node_swhid": "swh:1:cnt:<hash>;anchor=swh:1:rev:<commit>;path=/src/file.py"
```

These are dynamically resolved from Software Heritage using:

* `--repo-url`
* `--commit`, `--release-name`, or `--ref-name`

The result is a **fully qualified SWHID** that identifies a code fragment in a specific repository snapshot.

---

## Config File

`parsnips-config.json` is generated automatically or can be edited manually.

Key fields:

* `extract.extractions`: list of language-specific extraction configs
* `search`: search patterns, regex, unicode, include/exclude patterns
* `log`: quiet mode, log level, log file
* `strict`: fail fast on error

---

## Search Output

Running a search emits a structured JSON list of matched fragments:

```json
{
  "src/main.py::3": {
    "search_text": "def hello_world",
    "search_used_regex": false,
    "search_used_unicode": false,
    "search_regex_match_groups": null,
    "node_swhid": "swh:1:cnt:abcd...;anchor=swh:1:rev:1234;path=/src/main.py",
    "node_metadata": {
      "fragment_id": "src/main.py::3",
      "node_type": "FunctionDef",
      "text": "def hello_world():\n  print(\"Hello\")",
      ...
    }
  }
}
```

---

## CLI Options

Options used in the command line override those specified in `parsnips-config.json`. The CLI assumes it should extract fragments from source code for the `parsnips.json` unless specified to search, show the version, or delete the parsnips files.

| Argument              | Short | Default                                                         | Used For   | Description                                            |
| --------------------- | ----- | --------------------------------------------------------------- | ---------- | ------------------------------------------------------ |
| `--search`            | `-s`  | `None`                                                          | Search     | Text or pattern to search for                          |
| `--regex`             | `-r`  | `False`                                                         | Search     | Interpret search as a regular expression               |
| `--unicode`           | `-u`  | `False`                                                         | Search     | Normalize source and pattern using Unicode NFC         |
| `--language`          | `-l`  | `python`                                                        | Extraction | Programming language for extraction (e.g., `python`)   |
| `--include`           | `-i`  | `['*.py']`                                                      | Extraction | Glob(s) for included source files                      |
| `--exclude`           | `-e`  | from `.gitignore`                                               | Extraction | Glob(s) for excluded source files                      |
| `--extractor-class`   | —     | `parsnips.extractors.tree_sitter_extractor.TreeSitterExtractor` | Extraction | Fully qualified Python class path for custom extractor |
| `--searcher-class`    | —     | `parsnips.searchers.parsnips_searcher.ParsnipsSearcher`         | Search     | Fully qualified Python class path for custom searcher  |
| `--repo-url`          | —     | inferred from Git                                               | Search     | Repository origin URL (for SWHID context)              |
| `--commit`            | —     | `None`                                                          | Search     | Commit SHA                                             |
| `--release-name`      | —     | `None`                                                          | Search     | Git annotated tag                                      |
| `--ref-name`          | —     | `None`                                                          | Search     | Branch or lightweight tag                              |
| `--visit`             | —     | `None`                                                          | Search     | Specific snapshot visit ID                             |
| `--repo-root`         | —     | `cwd`                                                           | Extraction | Override repo root                                     |
| `--start-line-number` | —     | `None`                                                          | Search     | Start line (1-indexed)                                 |
| `--start-col-offset`  | —     | `None`                                                          | Search     | Start column (0-indexed)                               |
| `--end-line-number`   | —     | `None`                                                          | Search     | End line (1-indexed)                                   |
| `--end-col-offset`    | —     | `None`                                                          | Search     | End column (0-indexed)                                 |
| `--log-level`         | —     | `INFO`                                                          | Both       | Log level (DEBUG, INFO, WARNING...)                    |
| `--log`               | `-g`  | `None`                                                          | Both       | Path to JSON log file                                  |
| `--quiet`             | `-q`  | `False`                                                         | Both       | Suppress stdout logs                                   |
| `--strict`            | —     | `True`                                                          | Both       | Abort on first error                                   |
| `--delete`            | `-d`  | `False`                                                         | Neither    | Deletes `parsnips.json` and `parsnips-config.json`     |
| `--version`           | `-v`  | `False`                                                         | Neither    | Show version                                           |

---

## Logging and Strict Mode

You can control logging using:

* `--quiet` to suppress stdout
* `--log` to write to a file
* `--log-level` to set verbosity
* `--strict` to fail on first error

---

## Requirements

* Python 3.12+
* Dependencies (see `pyproject.toml`) include:

  * `pydantic`
  * `tree-sitter-language-pack`
  * `libcst`
  * `regex`
  * `ijson`
  * `pathspec`

---

## Licensing

Parsnips is licensed under the **Apache License 2.0**.

```
SPDX-License-Identifier: Apache-2.0
```

---

## Citation

If you use Parsnips in research or tools, please cite it using metadata from:

```
CITATION.cff
```

---

## Author

**Will Riley** — [wanderingwill@gmail.com](mailto:wanderingwill@gmail.com)

---

## Related Projects

* [Software Heritage](https://www.softwareheritage.org/)
* [SWHID Specification](https://docs.softwareheritage.org/devel/swh-model/#swh-ids)

---

## Disclaimer

Parsnips is an experimental tool designed for research and archival workflows. Use with care. Feedback and contributions are welcome.
