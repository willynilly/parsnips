from __future__ import annotations

from pathlib import Path
from typing import List, Union

from parsnips.models.parsnips_base_model import ParsnipsBaseModel
from parsnips.models.patterns.glob import Glob
from parsnips.models.patterns.regex import Regex


class PatternSet(ParsnipsBaseModel):
    regex: List[Regex]
    glob: List[Glob]

    def any_matches(self, value: Union[str, Path]) -> bool:
        val_str = str(value)

        for regex in self.regex:
            if regex.match(val_str):
                return True

        for glob in self.glob:
            if glob.matches(val_str):
                return True

        return False
