
from __future__ import annotations

import json
import logging
import sys
from typing import Type, TypeVar, cast

from pydantic import BaseModel, ValidationError

SelfModel = TypeVar("SelfModel", bound="ParsnipsBaseModel")


class ParsnipsBaseModel(BaseModel):

    def to_pretty_json(self, ensure_ascii=False, indent=2):
        return json.dumps(self.model_dump(mode="json"), ensure_ascii=ensure_ascii, indent=indent)


    @classmethod
    def model_validate_or_exit(cls: Type[SelfModel], data: dict | None = None, **kwargs) -> SelfModel:
        try:
            return cast(SelfModel, cls.model_validate(data or {}, **kwargs))
        except ValidationError as e:
            logger = logging.getLogger("parsnips")
            logger.error(f"Validation error in {cls.__name__}:\n{e}")
            sys.exit(1)