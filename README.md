# Parsnips

Create SWHIDs for Python classes, functions, and other source code fragments based on their abstract syntax tree (AST).

## Overview

**Parsnips** is a Python tool that analyzes Python source files using the built-in `ast` module and `asttokens` to create fine-grained, reproducible identifiers for fragments of Python code. It is designed to support persistent software identifiers (SWHIDs) for structural code elements such as:

- Functions
- Classes
- Assignments
- Expressions
- Other AST nodes

The resulting parse tree is exported into a fully deterministic folder structure, where each node:

- Is stored in a dedicated folder inside a hidden `.parsnips` directory.
- Contains the exact source text corresponding to the node.
- Includes structured metadata for precise archival referencing.

## Extraction Protocol

When Parsnips processes a Python file or directory, it follows this deterministic protocol:

1. **Unified Extraction Root**:

   - Regardless of whether you provide a file or directory as input, Parsnips always creates a `.parsnips/` subdirectory inside the directory where the file or directory resides.
   - This ensures a fully consistent and predictable output structure.

2. **Recursive Directory Traversal (when processing directories):**

   - Parsnips walks the entire directory tree starting at the input path.
   - It identifies all `.py` files to process.
   - Symlinks are not followed.
   - Any pre-existing `.parsnips/` subdirectories are deleted and regenerated to ensure full reproducibility.

3. **Per-File Processing:**

   - For each Python file, Parsnips parses the Abstract Syntax Tree (AST) using `ast` and `asttokens`.
   - The content SWHID for the entire file is computed using Python's `hashlib.blake2s()` directly, fully following the Software Heritage content SWHID specification, without external library dependencies.

4. **Node Processing:**

   - Each AST node is visited in traversal order.
   - If a node lacks a line number, it inherits the nearest parent node’s line number.
   - Each node is assigned:
     - Its AST type (e.g., `FunctionDef`, `ClassDef`, `Assign`).
     - A label (e.g., function name, class name, or a sanitized version of the assigned target for assignments).
   - A deterministic folder is created for each node with the structure:
     ```
     L{lineno}C{col_offset}T{traversal_index}__{node_type}__{node_label}
     ```

5. **Label Sanitization:**

   - To ensure filesystem-safe and portable folder names, labels are strictly sanitized:
     - Only characters `A-Z`, `a-z`, `0-9`, `_`, and `-` are allowed.
     - All other characters (including spaces, parentheses, brackets, symbols, and punctuation) are replaced with underscores (`_`).

6. **Outputs Generated:**

   For each node folder, Parsnips creates one file:

   ### `node_metadata.json`

   - Contains structured metadata for the AST node including:
     - `type`: The AST node type (e.g. `FunctionDef`).
     - `label`: The unsanitized label of the node.
     - `text`: The exact source text fragment for the node.
     - `lineno`: The node’s declared line number (or `null` if absent).
     - `effective_lineno`: The inherited line number after normalization.
     - `col_offset`: The column offset of the node.
     - `file_swhid`: The SWHID of the full source file.

7. **Directory Structure:**

   - The extraction output for each processed file is always written into:
     ```
     {parent_dir}/.parsnips/parsnips__{file_stem}__{file_ext}/
     ```

8. **Folder Sorting:**

   - Folders are deterministically named using the inherited line number, column offset, and traversal index.
   - Sorting is lexicographic but naturally places nodes with lower line numbers first.

## Fragment-Level SWHIDs

- The content SWHID for each node fragment is not generated during extraction.
- Instead, the `node_metadata.json` file itself becomes the fragment boundary.
- The fragment SWHID is computed as the `blake2s()` hash over the serialized `node_metadata.json` content.
- This ensures the SWHID includes full structural and textual information, not just the raw source text.

## Linking SWHIDs with Anchor Qualifiers

Fragment-level SWHIDs can be paired with the file SWHID using SWHID's *anchor* qualifier.

For example:

- File SWHID:
  ```
  swh:1:cnt:abcdef1234567890abcdef1234567890abcdef12
  ```
- Fragment SWHID:
  ```
  swh:1:cnt:fedcba0987654321fedcba0987654321fedcba09
  ```
- Anchored form:
  ```
  swh:1:cnt:fedcba0987654321fedcba0987654321fedcba09;anchor=swh:1:cnt:abcdef1234567890abcdef1234567890abcdef12
  ```

This allows the fragment to be fully tied to the exact version of its parent file.

## CLI Parameters

Parsnips provides multiple command-line options:

| Argument   | Description                                                                                 |
| ---------- | ------------------------------------------------------------------------------------------- |
| `-p` or `--path`     | Path to file or directory to process                                                        |
| `-c` or `--clean`  | Delete all `.parsnips` folders recursively                                                  |
| `-s` or `--search` | Search using a regular expression inside the `text` field of all `node_metadata.json` files |
| `-n` or `--normalize-search` | Apply Unicode normalization (NFC) to both the search pattern and node text before regex matching. This only applies to search operations and does not affect extraction. Extraction always preserves exact byte content for archival integrity. |
| `-q` or `--quiet`  | Suppress console output                                                                     |
| `-l` or `--logfile`    | Write logs to specified JSON file                                                                     |
| `--strict` | Fail immediately on first error or missing .parsnips folder                                                            |

## Example Usage

### Process a directory recursively:

```bash
parsnips path/to/my/project
```

- This will recursively process all `.py` files under `path/to/my/project`, generate `.parsnips/` directories for each directory containing Python files, and populate these directories with metadata files for the extracted fragment-level outputs.

### Process a single file:

```bash
parsnips path/to/file.py
```

- This will process only the single file `file.py` and output results to:

```bash
path/to/.parsnips/parsnips__file__py/
```

#### Example Input file `example.py`:

```python
class MyClass:
    def foo(self, x, y=(1, 2)):
        return x * y[0]

result = MyClass().foo(10)
```

#### Example Output structure:

```bash
.parsnips/parsnips__example__py/
  L1C0T1__ClassDef__MyClass/
    L2C4T2__FunctionDef__foo/
      L3C8T3__Return__node/
  L5C0T4__Assign__result_MyClass__foo_10/
```

### Search for the SWHID of a code fragment by using regular expressions for the source code fragment

You can use Parsnips to search for the SWHID of a code fragment by using regular expressions that match on the text of the code fragment.

#### Example Search Usage

Suppose you have already extracted a directory and want to search for any AST nodes containing `"hello world"`.

Run:

```bash
parsnips path/to/my/project --search "hello world"
```

Example output:

```json
{
  ".parsnips/parsnips__example__py/L8C4T7__Return__node/node_metadata.json": {
    "node_swhid": "swh:1:cnt:1234567890abcdef1234567890abcdef12345678",
    "node_metadata": {
      "type": "Return",
      "label": "node",
      "text": "return \"hello world\"",
      "lineno": 8,
      "effective_lineno": 8,
      "col_offset": 4,
      "file_swhid": "swh:1:cnt:abcdef1234567890abcdef1234567890abcdef12"
    }
  },
  ".parsnips/parsnips__example__py/L9C0T8__Constant__hello_world/node_metadata.json": {
    "node_swhid": "swh:1:cnt:fedcba0987654321fedcba0987654321fedcba09",
    "node_metadata": {
      "type": "Constant",
      "label": "hello world",
      "text": "\"hello world\"",
      "lineno": 9,
      "effective_lineno": 9,
      "col_offset": 0,
      "file_swhid": "swh:1:cnt:abcdef1234567890abcdef1234567890abcdef12"
    }
  }
}
```

If run with `--strict` mode and `.parsnips` folders are missing, the command will fail instead of silently returning empty results.


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