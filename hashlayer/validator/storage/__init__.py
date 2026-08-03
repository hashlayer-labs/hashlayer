"""Validator storage package.

Public API preserved from the former ``storage.py`` module:
``JsonValidatorStorage``, ``RedisValidatorStorage``, ``get_validator_storage``.
"""

from hashlayer.validator.storage.factory import STORAGE_CLASSES, get_validator_storage
from hashlayer.validator.storage.json_storage import JsonValidatorStorage
from hashlayer.validator.storage.redis_storage import RedisValidatorStorage

__all__ = [
    "JsonValidatorStorage",
    "RedisValidatorStorage",
    "STORAGE_CLASSES",
    "get_validator_storage",
]
