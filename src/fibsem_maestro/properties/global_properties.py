# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Any

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
        Accumulate a property value to microscope or beam properties.

        If the property object does not exist, it will be created with this property.
        If it exists, the value will be added to the existing property (using the
        __add__ operator).

        Args:
            property_name: Name of the property to accumulate.
            value_to_add: Value to add to the property.
            beam_type: Type of beam (ELECTRON, ION) or None for microscope properties.

        Raises:
            ValueError: If the property does not exist or does not support addition.
        """
        # determine which properties object to update
        props_attr_name = self.get_properties_attr_name(beam_type)
        inner_props: BeamProperties | MicroscopeProperties | None = getattr(
            self, props_attr_name
        )

        if inner_props is None:
            # create new properties object with this property
            self._initialize_properties(props_attr_name, property_name, value_to_add)
        else:
            # add to existing property
            self._accumulate_property_value(
                inner_props, property_name, value_to_add, props_attr_name
            )

    def set_property(
        self, property_name: str, value: Any, beam_type: BeamType | None = None
    ) -> None:
        """
        Set a property value, replacing any existing value.

        If the property object does not exist, it will be created with this property.
        If it exists, the property will be set to the new value without accumulation.

        Args:
            property_name: Name of the property to set.
            value: New value for the property.
            beam_type: Type of beam (ELECTRON, ION) or None for microscope properties.

        Raises:
            ValueError: If the property does not exist on an existing properties object.
        """
        props_attr_name = self.get_properties_attr_name(beam_type)
        inner_props: BeamProperties | MicroscopeProperties | None = getattr(
            self, props_attr_name
        )

        if inner_props is None:
            # Create new properties object with this property
            self._initialize_properties(props_attr_name, property_name, value)
        else:
            # Set the property on existing object
            self._set_property_value(inner_props, property_name, props_attr_name, value)

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
        properties_class = (
            BeamProperties if props_attr_name != "microscope" else MicroscopeProperties
        )
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
        Accumulate a value to an existing property using the __add__ operator.

        If the property is None, it will be set to value_to_add. Otherwise, the value
        will be added to the existing property using the __add__ operator.

        Args:
            inner_props: The properties object containing the property.
            property_name: Name of the property to update.
            value_to_add: Value to add to the existing property.
            props_attr_name: Name of the properties attribute (for error messages).

        Raises:
            ValueError: If property does not exist or does not support addition.
        """
        # check if property exists
        if not hasattr(inner_props, property_name):
            available_props = ", ".join(type(inner_props).model_fields.keys())
            raise ValueError(
                f"Property '{property_name}' does not exist on '{props_attr_name}'. "
                f"Available properties: {available_props}"
            )

        current_value = getattr(inner_props, property_name)

        # if property is None, just set it to the value
        if current_value is None:
            setattr(inner_props, property_name, value_to_add)
            return

        # check if property type supports addition
        if not hasattr(current_value, "__add__"):
            raise ValueError(
                f"Cannot accumulate property '{property_name}' on '{props_attr_name}': "
                f"type '{type(current_value).__name__}' does not support the addition operator"
            )

        # perform addition and update
        new_value = value_to_add + current_value
        setattr(inner_props, property_name, new_value)

    def _set_property_value(
        self,
        inner_props: BeamProperties | MicroscopeProperties,
        property_name: str,
        props_attr_name: str,
        value: Any,
    ) -> None:
        """
        Set a property value on an existing properties object.

        Args:
            inner_props: The properties object containing the property.
            property_name: Name of the property to set.
            props_attr_name: Name of the properties attribute (for error messages).
            value: New value for the property.

        Raises:
            ValueError: If property does not exist on the properties object.
        """
        # check if property exists in the model
        if property_name not in type(inner_props).model_fields:
            available_props = ", ".join(type(inner_props).model_fields.keys())
            raise ValueError(
                f"Property '{property_name}' does not exist on '{props_attr_name}'. "
                f"Available properties: {available_props}"
            )

        setattr(inner_props, property_name, value)
