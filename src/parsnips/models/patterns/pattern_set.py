from __future__ import annotations

from pathlib import Path
from typing import List, Union

import pathspec

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

        # since the order matters for glob patterns that involve negation
        # a spec is built using all the glob patterns
        glob_patterns: list[str] = [g.pattern for g in self.glob]    
        spec = pathspec.PathSpec.from_lines("gitwildmatch", glob_patterns)
        return spec.match_file(str(val_str))
