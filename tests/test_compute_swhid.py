import json

from parsnips.main import compute_swhid


def test_compute_swhid_known_value():
    sample_metadata = {
        "type": "FunctionDef",
        "label": "foo",
        "text": "def foo(x): return x",
        "lineno": 2,
        "effective_lineno": 2,
        "col_offset": 0,
        "file_swhid": "swh:1:cnt:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    }

    metadata_str = json.dumps(sample_metadata, sort_keys=True, ensure_ascii=False)
    expected_swhid = "swh:1:cnt:19ba7fcee22a2eded332850851070299943c2b328a37f882bbf3620ec4586939"
    computed_swhid = compute_swhid(metadata_str)

    assert computed_swhid == expected_swhid
