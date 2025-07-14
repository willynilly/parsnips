from __future__ import annotations

import hashlib
from pathlib import Path
from typing import BinaryIO, Union

from pydantic import BaseModel


class ParsnipsContentSwhid(BaseModel):
    swhid: str

    @classmethod
    def from_bytes(cls, content: bytes) -> ParsnipsContentSwhid:
        size = len(content)
        header = f"blob {size}\0".encode("utf-8")
        digest = hashlib.sha1(header + content).hexdigest()
        return cls(swhid=f"swh:1:cnt:{digest}")

    @staticmethod
    def from_string(content: str) -> ParsnipsContentSwhid:
        return ParsnipsContentSwhid.from_bytes(content.encode("utf-8"))

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> ParsnipsContentSwhid:
        path = Path(path)
        size = path.stat().st_size
        with path.open("rb") as f:
            return cls.from_stream(f, size)


    @classmethod
    def from_stream(cls, stream: BinaryIO, size: int) -> ParsnipsContentSwhid:
        sha1 = hashlib.sha1()
        sha1.update(f"blob {size}\0".encode("utf-8"))
        while chunk := stream.read(8192):
            sha1.update(chunk)
        return cls(swhid=f"swh:1:cnt:{sha1.hexdigest()}")

    def __str__(self) -> str:
        return self.swhid

    def to_swhid(self) -> str:
        return self.swhid
