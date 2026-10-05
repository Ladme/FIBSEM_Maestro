# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

import copy
from typing import Any, Self

from pydantic import Field

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.properties.microscope_properties import MicroscopeProperties
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.property_names import PropertyNames


class GlobalProperties(BaseSettings):
    microscope: MicroscopeProperties | None = Field(
        default=None,
        description="General properties of the microscope.",
    )
    electron_beam: BeamProperties | None = Field(
        default=None,
        description="Properties of the electron beam.",
    )
    ion_beam: BeamProperties | None = Field(
        default=None,
        description="Properties of the ion beam.",
    )

    def get_property_names(self) -> PropertyNames:
        """
        Return a list of all property names that are not None.

        Returns:
            PropertyNames: Collection of property names.
        """
        return PropertyNames(
            microscope=self.microscope.get_property_names() if self.microscope else [],
            electron_beam=self.electron_beam.get_property_names()
            if self.electron_beam
            else [],
            ion_beam=self.ion_beam.get_property_names() if self.ion_beam else [],
        )

    def accumulate_property(
        self, property_name: str, value_to_add: Any, beam_type: BeamType | None = None
    ) -> None:
        """
        Accumulate a value onto a microscope or beam property.

        Declared fields and extra properties are treated alike. A property that
        is not set (absent or `None`) is set to `value_to_add`; otherwise
        `value_to_add` is added to the current value with `+`.

        Args:
            property_name: Name of the property to accumulate.
            value_to_add: Value to add to the property.
            beam_type: Type of beam (ELECTRON, ION) or None for microscope properties.

        Raises:
            ValueError: If the name cannot be used as a property, or the current
                value does not support addition.
        """
        # determine which properties object to update
        props_attr_name = self.get_properties_attr_name(beam_type)
        self._check_property_name(props_attr_name, property_name)
        inner_props: BeamProperties | MicroscopeProperties | None = getattr(
            self, props_attr_name
        )

        if inner_props is None:
            self._initialize_properties(props_attr_name, property_name, value_to_add)
        else:
            self._accumulate_property_value(
                inner_props, property_name, value_to_add, props_attr_name
            )

    def set_property(
        self, property_name: str, value: Any, beam_type: BeamType | None = None
    ) -> None:
        """
        Set a microscope or beam property, replacing any existing value.

        Declared fields and extra properties are treated alike. If the
        properties object does not exist yet, it is created with this property.

        Args:
            property_name: Name of the property to set.
            value: New value for the property.
            beam_type: Type of beam (ELECTRON, ION) or None for microscope properties.

        Raises:
            ValueError: If the name cannot be used as a property.
        """
        props_attr_name = self.get_properties_attr_name(beam_type)
        self._check_property_name(props_attr_name, property_name)
        inner_props: BeamProperties | MicroscopeProperties | None = getattr(
            self, props_attr_name
        )

        if inner_props is None:
            self._initialize_properties(props_attr_name, property_name, value)
        else:
            setattr(inner_props, property_name, value)

    def get_properties_attr_name(self, beam_type: BeamType | None) -> str:
        """
        Map BeamType to the corresponding properties attribute name.

        Args:
            beam_type: Type of beam or None for microscope.

        Returns:
            The attribute name as a string.
        """
        match beam_type:
            case None:
                return "microscope"
            case BeamType.ELECTRON:
                return "electron_beam"
            case BeamType.ION:
                return "ion_beam"

    def select(self, names: PropertyNames) -> Self:
        """
        Return a new instance containing only the named properties.

        Both declared fields and extra properties can be selected.
        A property counts as set if it is not `None`.
        Values are deep-copied, so the result shares no mutable state with this instance.

        Args:
            names: The property names to keep.

        Returns:
            A new `GlobalProperties` with only the named properties set.

        Raises:
            KeyError: If any named property is not set on this instance.
        """
        selected = type(self)()
        for attr in ("microscope", "electron_beam", "ion_beam"):
            wanted: list[str] = list(getattr(names, attr))
            if not wanted:
                continue

            inner: BeamProperties | MicroscopeProperties | None = getattr(self, attr)
            if inner is None:
                raise KeyError(
                    f"No properties set on '{attr}'; requested: {', '.join(wanted)}."
                )

            values = {name: getattr(inner, name, None) for name in wanted}
            if missing := [name for name, value in values.items() if value is None]:
                raise KeyError(f"Properties not set on '{attr}': {', '.join(missing)}.")

            setattr(selected, attr, type(inner).model_validate(copy.deepcopy(values)))
        return selected

    def _initialize_properties(
        self,
        props_attr_name: str,
        property_name: str,
        value: Any,
    ) -> None:
        """
        Initialize a new properties object with a single property.

        Args:
            props_attr_name: Attribute name of the properties object.
            property_name: Name of the property to set.
            value: Value of the property.
        """
        properties_class = self._properties_class(props_attr_name)

        setattr(
            self,
            props_attr_name,
            properties_class.model_validate({property_name: value}),
        )

    def _accumulate_property_value(
        self,
        inner_props: BeamProperties | MicroscopeProperties,
        property_name: str,
        value_to_add: Any,
        props_attr_name: str,
    ) -> None:
        """
        Accumulate a value onto a property of an existing properties object.

        A property that is not set (absent or `None`) is set to
        `value_to_add`; otherwise the value is added with `+`.

        Args:
            inner_props: The properties object containing the property.
            property_name: Name of the property to update.
            value_to_add: Value to add to the existing property.
            props_attr_name: Name of the properties attribute (for error messages).

        Raises:
            ValueError: If the current value does not support addition.
        """
        current_value = getattr(inner_props, property_name, None)

        if current_value is None:
            setattr(inner_props, property_name, value_to_add)
            return

        if not hasattr(current_value, "__add__"):
            raise ValueError(
                f"Cannot accumulate property '{property_name}' on '{props_attr_name}': "
                f"type '{type(current_value).__name__}' does not support the addition operator"
            )

        setattr(inner_props, property_name, value_to_add + current_value)

    @staticmethod
    def _properties_class(
        props_attr_name: str,
    ) -> type[BeamProperties] | type[MicroscopeProperties]:
        """
        Return the properties model stored under an attribute name.

        Args:
            props_attr_name: `"microscope"`, `"electron_beam"` or `"ion_beam"`.

        Returns:
            The model class for that attribute.
        """
        return (
            MicroscopeProperties if props_attr_name == "microscope" else BeamProperties
        )

    @classmethod
    def _check_property_name(cls, props_attr_name: str, property_name: str) -> None:
        """
        Reject names that cannot be stored as properties.

        Any declared field or extra name is a valid property, except names
        starting with an underscore, which Pydantic does not store as extras,
        and names that collide with attributes of the model (methods,
        Pydantic internals).

        Args:
            props_attr_name: Attribute name of the properties object.
            property_name: The property name to check.

        Raises:
            ValueError: If the name cannot be used as a property.
        """
        properties_class = cls._properties_class(props_attr_name)
        if property_name in properties_class.model_fields:
            return
        if property_name.startswith("_") or hasattr(properties_class, property_name):
            raise ValueError(
                f"'{property_name}' cannot be used as a property name on "
                f"'{props_attr_name}': it starts with an underscore or collides "
                f"with an attribute of {properties_class.__name__}."
            )
