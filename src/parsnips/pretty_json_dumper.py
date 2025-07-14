import json

from pydantic import BaseModel


class PrettyJsonDumper:
    INDENT = 2
    ENSURE_ASCII = False

    @classmethod
    def dumps(cls, obj) -> str:
        if isinstance(obj, BaseModel):
            return json.dumps(obj.model_dump(mode="json"), ensure_ascii=cls.ENSURE_ASCII, indent=cls.INDENT)

        return json.dumps(obj, indent=cls.INDENT, ensure_ascii=cls.ENSURE_ASCII)
    
    @classmethod
    def dump(cls, obj, f):
        json.dump(obj, f, indent=cls.INDENT, ensure_ascii=cls.ENSURE_ASCII)
