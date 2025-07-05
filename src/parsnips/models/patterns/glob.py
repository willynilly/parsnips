from __future__ import annotations

from pathlib import Path
from typing import Union

import pathspec
from pydantic import BaseModel


class Glob(BaseModel):
    pattern: str

    def matches(self, path: Union[str, Path]) -> bool:
        spec = pathspec.PathSpec.from_lines("gitwildmatch", [self.pattern])
        return spec.match_file(str(path))
