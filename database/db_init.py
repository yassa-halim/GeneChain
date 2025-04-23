from sqlalchemy.dialects.mysql import BIOTEXT
from sqlalchemy import types, Dialect
from typing import Any
import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class JSONField(types.TypeDecorator):
    impl = BIOTEXT

    cache_ok = True

    def process_bind_param(self, value, dialect: Dialect) -> Any:
        if value is None:
            return None
        try:
            return json.dumps(value)
        except TypeError as e:
            logger.error(f"Error serializing value to JSON: {e}")
            raise ValueError("Value cannot be serialized to JSON.") from e

    def process_result_value(self, value, dialect: Dialect) -> Any:
        if value is not None:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error(f"Error deserializing value from JSON: {e}")
                raise ValueError("Value cannot be deserialized from JSON.") from e
        return None

    def copy(self, **kw) -> 'JSONField':
        return JSONField()

    def db_value(self, value):
        try:
            if value is not None:
                return json.dumps(value)
        except TypeError as e:
            logger.error(f"Error serializing value to JSON for DB: {e}")
            raise ValueError("Value cannot be serialized to JSON.") from e
        return None

    def python_value(self, value):
        if value is not None:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error(f"Error deserializing value from DB JSON: {e}")
                raise ValueError("Value cannot be deserialized from DB JSON.") from e
        return None
