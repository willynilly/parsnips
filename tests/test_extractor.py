import json
import logging
import tempfile
from pathlib import Path

import pytest

from parsnips.extractors.parsnips_extractor import ParsnipsExtractor
from parsnips.utils import get_parsnips_version


@pytest.fixture
def parsnips_version():
    return get_parsnips_version()

@pytest.fixture
def source_file_languages():
    return ['python']

@pytest.fixture
def simple_python_code():
    return '''class MyClass:
    def foo(self, x, y=(1, 2)):
        return x * y[0]

result = MyClass().foo(10)
'''

@pytest.fixture
def logger():
    logger = logging.getLogger("parsnips")
    logger.setLevel(logging.CRITICAL)

@pytest.fixture
def extractor(parsnips_version, source_file_languages, logger):
    return ParsnipsExtractor(parsnips_version=parsnips_version, source_file_languages=source_file_languages, strict=True)

def test_extraction_creates_expected_output(extractor, simple_python_code):
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "example.py"
        file_path.write_text(simple_python_code, encoding="utf-8")

        extractor.process(file_path)

        parsnips_root = Path(tmpdir) / ".parsnips"
        assert parsnips_root.exists(), ".parsnips directory was not created"

        subdirs = [d for d in parsnips_root.iterdir() if d.is_dir()]
        assert subdirs, "No output subdirectories found in .parsnips"
        output_dir = subdirs[0]

        # Check that at least some node folders exist (recursively)
        node_folders = list(output_dir.rglob("*"))
        node_dirs = [f for f in node_folders if f.is_dir()]
        assert len(node_dirs) > 0

        # Look for FunctionDef in any subdirectory
        found = any("FunctionDef" in folder.name for folder in node_dirs)
        assert found

        # Verify node_metadata.json exists and has correct structure
        for folder in node_dirs:
            node_meta = folder / "node_metadata.json"
            assert node_meta.exists()
            with node_meta.open(encoding="utf-8") as f:
                metadata = json.load(f)
            assert "type" in metadata
            assert "label" in metadata
            assert "text" in metadata
            assert "lineno" in metadata
            assert "effective_lineno" in metadata
            assert "col_offset" in metadata
            assert "file_swhid" in metadata
