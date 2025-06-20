import json


class PrettyJsonDumper:
    INDENT = 2
    ENSURE_ASCII = False

    @classmethod
    def dumps(cls, obj) -> str:
        return json.dumps(obj, indent=cls.INDENT, ensure_ascii=cls.ENSURE_ASCII)
    
    @classmethod
    def dump(cls, obj, f):
        json.dump(obj, f, indent=cls.INDENT, ensure_ascii=cls.ENSURE_ASCII)
