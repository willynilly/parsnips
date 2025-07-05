import logging
import tempfile
from pathlib import Path

import pytest

from parsnips.extractors.parsnips_extractor import ParsnipsExtractor
from parsnips.models.config.parsnips_config import ParsnipsConfig
from parsnips.models.extraction import Extraction
from parsnips.utils import get_parsnips_cli_version


@pytest.fixture
def parsnips_cli_version():
    return get_parsnips_cli_version()

@pytest.fixture
def source_file_language():
    return 'python'

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
def parsnips_config():
    return ParsnipsConfig.from_json_file(Path(__file__).parent.parent / 'json_fixtures' / 'test-parsnips-config.json')

@pytest.fixture
def extraction_config(parsnips_config):
    extraction_config = parsnips_config.extract.extractions[0]
    return extraction_config
    
@pytest.fixture
def extractor(parsnips_config, extraction_config):
    return ParsnipsExtractor(parsnips_config=parsnips_config, extraction_config=extraction_config)

def test_extraction_creates_expected_output(extractor, parsnips_config, source_file_language, simple_python_code):
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        file_path = repo_root / "example.py"
        file_path.write_text(simple_python_code, encoding="utf-8")

        extractions: list[Extraction] = []
        extraction: Extraction = extractor.extract(file_path)
        assert extraction.extraction_config.language == source_file_language, "extraction configuration has wrong language"
        extractions.append(extraction)

        ParsnipsExtractor.save(parsnips_config=parsnips_config, extractions=extractions, repo_root=repo_root)

        parsnips_json = repo_root / "parsnips.json"
        assert parsnips_json.exists(), "parsnips.json was not created"