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
     - This ensures compatibility across all operating systems and archival storage systems.

6. **Outputs Generated:**

   For each node folder, Parsnips creates two files:

   ### 1. `node_text.txt`

   - Contains the exact source code fragment for the AST node as extracted by `asttokens.get_text()`.
   - This text is **not normalized** to preserve archival integrity.
   - This file's content is hashed using `hashlib.blake2s()` to generate a fragment-level SWHID following the Software Heritage specification.

   ### 2. `node_metadata.json`

   - Contains structured metadata for the AST node including:
     - `type`: The AST node type (e.g. `FunctionDef`).
     - `lineno`: The node’s declared line number (or `null` if absent).
     - `effective_lineno`: The inherited line number after normalization.
     - `col_offset`: The column offset of the node.
     - `file_swhid`: The SWHID of the full source file.
     - `node_swhid`: The content SWHID for the node's source text.

7. **Directory Structure:**

   - The extraction output for each processed file is always written into:
     ```
     {parent_dir}/.parsnips/parsnips__{file_stem}__{file_ext}/
     ```

8. **Folder Sorting:**

   - Folders are deterministically named using the inherited line number, column offset, and traversal index.
   - Sorting is lexicographic but naturally places nodes with lower line numbers first.
   - Nodes missing line numbers inherit their parent’s line number, ensuring children follow their parents naturally.

## Linking SWHIDs with Anchor Qualifiers

The node-level SWHIDs generated for each `node_text.txt` file can be paired with the SWHID of the full file using SWHID's *anchor* qualifier.

For example, suppose:

- The full file SWHID is:\
  `swh:1:cnt:abcdef1234567890abcdef1234567890abcdef12`

- The node fragment SWHID is:\
  `swh:1:cnt:fedcba0987654321fedcba0987654321fedcba09`

A qualified fragment-level identifier can be constructed:

```
swh:1:cnt:fedcba0987654321fedcba0987654321fedcba09;anchor=swh:1:cnt:abcdef1234567890abcdef1234567890abcdef12
```

This allows the fragment identifier to be explicitly anchored to its parent file in accordance with the Software Heritage SWHID specification for content-addressable fragment identification.

## Motivation

Parsnips was developed to enable fragment-level archival of Python code within content-addressable archives such as [Software Heritage](https://www.softwareheritage.org/). While Software Heritage currently provides content identifiers for full source files, Parsnips enables generating reproducible identifiers for fine-grained code elements tied directly to the abstract syntax tree.

The goal is to enable:

- Reproducible code citation
- Sub-file archival
- Persistent identifiers for code fragments
- Long-term scientific reproducibility

## Example Usage

### Process a directory recursively:

```bash
parsnips path/to/my/project
```

- This will recursively process all `.py` files under `path/to/my/project`, generate `.parsnips/` directories for each directory containing Python files, and populate these directories with the extracted fragment-level outputs.

### Process a single file:

```bash
parsnips path/to/file.py
```

- This will process only the single file `file.py` and output results to:

```bash
path/to/.parsnips/parsnips__file__py/
```

## Example Input and Output

### Example input file `example.py`:

```python
class MyClass:
    def foo(self, x, y=(1, 2)):
        return x * y[0]

result = MyClass().foo(10)
```

### Example output directory:

```bash
.parsnips/parsnips__example__py/
  L1C0T1__ClassDef__MyClass/
    L2C4T2__FunctionDef__foo/
      L3C8T3__Return__node/
  L5C0T4__Assign__result_MyClass__foo_10
```

- Note that characters like `(`, `)`, `,`, and `.` have been sanitized into underscores (`_`) in the folder names.

## Contributing

Pull requests and contributions are welcome!

To set up your development environment:

```bash
git clone https://github.com/willynilly/parsnips.git
cd parsnips
pip install -e .[testing,dev]
pre-commit install -t pre-commit -t pre-push
pre-commit run --all-files
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

