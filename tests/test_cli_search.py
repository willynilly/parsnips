import json
import logging
import tempfile
from pathlib import Path

import pytest

from parsnips.extractors.parsnips_extractor import ParsnipsExtractor
from parsnips.searchers.parsnips_searcher import ParsnipsSearcher
from parsnips.swhid import Swhid
from parsnips.utils import get_parsnips_version


@pytest.fixture
def sample_python_code():
    return '''class MyClass:
    def foo(self, x, y=(1, 2)):
        return x * y[0]

result = MyClass().foo(10)

class AnotherClass:
    def bar(self):
        return "hello world"
'''

@pytest.fixture
def parsnips_version():
    return get_parsnips_version()

@pytest.fixture
def logger():
    logger = logging.getLogger("parsnips-test")
    logger.setLevel(logging.CRITICAL)
    return logger

@pytest.fixture
def extractor(parsnips_version, logger):
    return ParsnipsExtractor(parsnips_version=parsnips_version, logger=logger, strict=True)

@pytest.fixture
def searcher(parsnips_version, logger):
    return ParsnipsSearcher(parsnips_version=parsnips_version, logger=logger)


def test_precise_search_functionality(extractor, searcher, logger, sample_python_code):
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "example.py"
        file_path.write_text(sample_python_code, encoding="utf-8")

        # Extract the file
        extractor.process(file_path)

        # Perform search
        base_dir = Path(tmpdir)
        pattern = 'hello world'
        results = searcher.search(base_dir, pattern)

        # Build expectations as tuples of (type, label)
        expected_nodes = {
            ("Module", "node"),
            ("ClassDef", "AnotherClass"),
            ("FunctionDef", "bar"),
            ("Return", "node"),
            ("Constant", "hello world"),
        }

        found_nodes = set()

        for rel_path, data in results.items():
            assert rel_path.endswith("node_metadata.json")
            assert "node_swhid_without_qualifiers" in data
            assert "node_metadata" in data

            node_meta = data["node_metadata"]
            found_nodes.add((node_meta["type"], node_meta["label"]))

            # Verify that "hello world" exists in node text
            assert pattern in node_meta["text"]

            # Independently recompute SWHID and verify
            metadata_str = json.dumps(node_meta, sort_keys=True, ensure_ascii=False)
            expected_swhid = Swhid.compute_content_swhid(metadata_str)
            assert data["node_swhid_without_qualifiers"] == expected_swhid

        # Finally, ensure all expected nodes were found
        assert found_nodes == expected_nodes
