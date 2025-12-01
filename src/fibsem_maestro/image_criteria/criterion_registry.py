# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Callable
from typing import TYPE_CHECKING

import numpy as np

from fibsem_maestro.image_criteria.error import CriterionError

if TYPE_CHECKING:
    from fibsem_maestro.core.image import Image
    from fibsem_maestro.logging.text.text_logger import TextLogger
    from fibsem_maestro.settings.criterion_settings import (
        CriterionSettings,
    )

CriterionFunction = Callable[["Image", "CriterionSettings", "TextLogger"], np.floating]


class CriterionRegistry:
    """
    Registry for criterion functions.

    The registry stores functions that implement criteria for evaluating image quality.
    Each function must have the signature:

        (img: Image, settings: CriterionSettings) -> np.floating

    Constructing the class with a criterion name returns the corresponding
    registered function. Example:

        fn = CriterionRegistry("bandpass")
        result = fn(img, settings)

    Attributes:
        _registry (dict[str, CriterionFunction]):
            Internal dictionary mapping criterion names to their functions.
    """

    _registry: dict[str, CriterionFunction] = {}

    @classmethod
    def get(cls, name: str) -> CriterionFunction:
        """
        Return the registered function associated with the given name.

        Args:
            name (str): The name of the criterion function to retrieve.

        Returns:
            CriterionFunction: The corresponding registered function.

        Raises:
            CriterionError: If the given name is not registered.
        """
        if name not in cls._registry:
            raise CriterionError(f"Criterion '{name}' is not registered.")
        return cls._registry[name]

    @classmethod
    def register(cls, name: str) -> Callable[[CriterionFunction], CriterionFunction]:
        """
        Decorator that registers a criterion function under a given name.

        Example::

            @CriterionRegistry.register("bandpass")
            def bandpass_criterion(img, settings):
                ...

        Args:
            name (str): The name under which to register the function.

        Returns:
            Callable[[CriterionFunction], CriterionFunction]:
                A decorator that registers the function and returns it unchanged.

        Raises:
            CriterionError: If the name is already registered.
        """

        def decorator(func: CriterionFunction) -> CriterionFunction:
            if name in cls._registry:
                raise CriterionError(f"Criterion '{name}' is already registered.")
            cls._registry[name] = func
            return func

        return decorator

    @classmethod
    def has(cls, name: str) -> bool:
        """
        Check whether a criterion name is registered.

        Args:
            name (str): The name to check.

        Returns:
            bool: True if the name exists in the registry, False otherwise.
        """
        return name in cls._registry

    @classmethod
    def allowed(cls) -> list[str]:
        """
        Return a list of all registered criterion names.

        Returns:
            list[str]: A list of criterion names currently registered.
        """
        return list(cls._registry)
