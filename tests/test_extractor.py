import json
import logging
import tempfile
from pathlib import Path

import pytest

from parsnips.extractor import ParsnipsExtractor


@pytest.fixture
def simple_python_code():
    return '''class MyClass:
    def foo(self, x, y=(1, 2)):
        return x * y[0]

result = MyClass().foo(10)
'''

@pytest.fixture
def extractor():
    logger = logging.getLogger("parsnips-test")
    logger.setLevel(logging.CRITICAL)
    return ParsnipsExtractor(logger=logger, strict=True)

def test_extraction_creates_expected_output(extractor, simple_python_code):
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "example.py"
        file_path.write_text(simple_python_code, encoding="utf-8")

        extractor.process(file_path)

        output_dir = Path(tmpdir) / ".parsnips" / "parsnips__example__py"
        assert output_dir.exists()

        # Check that at least some node folders exist (recursively)
        node_folders = list(output_dir.rglob("*"))
        node_dirs = [f for f in node_folders if f.is_dir()]
        assert len(node_dirs) > 0

        # Look for FunctionDef__foo in any subdirectory
        found = any("FunctionDef__foo" in folder.name for folder in node_dirs)
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
