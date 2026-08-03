"""Validator storage factory."""

from typing import Union

from bittensor.core.config import Config
from bittensor.utils.btlogging import logging

from hashlayer.validator.storage.json_storage import JsonValidatorStorage
from hashlayer.validator.storage.redis_storage import RedisValidatorStorage

STORAGE_CLASSES = {"json": JsonValidatorStorage, "redis": RedisValidatorStorage}


# Factory function to get storage
def get_validator_storage(
    storage_type: str, config: "Config"
) -> Union["JsonValidatorStorage", "RedisValidatorStorage"]:
    """Get a Validator storage instance based on a passed storage type.

    Arguments:
        storage_type: The type of storage to initialize.
        config: The configuration object.

    Returns:
        Storage instance created based on the specified storage type.
    """
    if storage_type not in STORAGE_CLASSES:
        raise ValueError(f"Unknown storage type: {storage_type}")

    storage_class = STORAGE_CLASSES[storage_type]

    try:
        return storage_class(config)
    except Exception as e:
        message = f"Failed to initialize {storage_type} storage: {e}"
        logging.error(message)
        raise Exception(message)
