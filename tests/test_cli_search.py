import logging
from pathlib import Path

import pytest

from parsnips.extractors.libcst_extractor import LibCSTExtractor
from parsnips.extractors.parsnips_extractor import ParsnipsExtractor
from parsnips.models.config.parsnips_config import ParsnipsConfig
from parsnips.models.extraction import Extraction
from parsnips.searchers.parsnips_searcher import ParsnipsSearcher


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
def sample_python_code_path(tmp_path, sample_python_code):
    p = tmp_path / "sample_python_code.py"
    p.write_text(sample_python_code, encoding="utf-8")
    return p

@pytest.fixture
def logger():
    logger = logging.getLogger("parsnips")
    logger.setLevel(logging.CRITICAL)
    return logger

@pytest.fixture
def parsnips_config():
    return ParsnipsConfig.from_json_file(Path(__file__).parent / 'json_fixtures' / 'test-parsnips-config.json')

@pytest.fixture
def extraction_config(parsnips_config):
    return parsnips_config.extract.extractions[0]

@pytest.fixture
def parsnips_file_path(tmp_path):
    return tmp_path / "parsnips.json"

@pytest.fixture
def git_dir_path(tmp_path):
    p = tmp_path / ".git"
    # Create a dummy .git directory
    p.mkdir(parents=True, exist_ok=True)
    return p

@pytest.fixture
def libcst_extractor(parsnips_file_path, parsnips_config, extraction_config):
    return LibCSTExtractor(parsnips_file_path=parsnips_file_path, parsnips_config=parsnips_config, extraction_config=extraction_config)

@pytest.fixture
def searcher(parsnips_config):
    return ParsnipsSearcher(parsnips_config=parsnips_config)

def test_cli_search_by_keyword_without_regex(tmp_path, git_dir_path, sample_python_code_path, parsnips_file_path, libcst_extractor, searcher):

    # make sure the regex is not used for the search
    assert not libcst_extractor.parsnips_config.search.use_regex 

    # Extract the file
    extraction: Extraction = libcst_extractor.extract()

    ParsnipsExtractor.save(parsnips_file_path=parsnips_file_path, parsnips_config=libcst_extractor.parsnips_config, extractions=[extraction])

    # Perform search
    search_text = 'hello world'
    results: dict = searcher.search(parsnips_file_path=parsnips_file_path, search_text=search_text)

    expected_nodes: set = {
        ("sample_python_code.py::1", "Module")
    }

    blacklist_words: list[str] = ["MyClass", "foo", "y="]

    found_nodes: set = set()

    for fragment_id, data in results.items():
        assert fragment_id.startswith("sample_python_code.py::")
        assert "node_swhid_without_qualifiers" in data
        assert "node_metadata" in data

        node_meta = data["node_metadata"]
        
        # Verify that "hello world" exists in node text
        assert search_text in node_meta["text"]

        # verify that for non-module level nodes certain text was not found
        if node_meta["node_type"] != "Module":
            for blacklist_word in blacklist_words:
                assert blacklist_word not in node_meta["text"]

        found_nodes.add((fragment_id, node_meta['node_type']))        

    assert expected_nodes <= found_nodes