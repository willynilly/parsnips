
from __future__ import annotations

import logging
import sys
from typing import Any, Type, TypeVar, cast

from pydantic import BaseModel, ValidationError

from parsnips.pretty_json_dumper import PrettyJsonDumper

SelfModel = TypeVar("SelfModel", bound="ParsnipsBaseModel")


class ParsnipsBaseModel(BaseModel):

    def to_pretty_json(self) -> str:
        return PrettyJsonDumper.dumps(self)

    @classmethod
    def model_validate_or_exit(cls: Type[SelfModel], data: dict[str, Any] | None = None, **kwargs) -> SelfModel:
        try:
            return cast(SelfModel, cls.model_validate(data or {}, **kwargs))
        except ValidationError as e:
            logger = logging.getLogger("parsnips")
            logger.error(f"Validation error in {cls.__name__}:\n{e}")
            sys.exit(1)