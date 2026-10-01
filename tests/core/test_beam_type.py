# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from fibsem_maestro.core.beam_type import BeamType


def test_beam_type_electron_int_is_one():
    assert int(BeamType.ELECTRON) == 1


def test_beam_type_ion_int_is_two():
    assert int(BeamType.ION) == 2


def test_beam_type_str_returns_value_not_qualified_name():
    assert str(BeamType.ELECTRON) == "electron"
    assert str(BeamType.ION) == "ion"


def test_beam_type_lookup_by_value_returns_member():
    assert BeamType("electron") is BeamType.ELECTRON
    assert BeamType("ion") is BeamType.ION


def test_beam_type_members_are_distinct():
    assert BeamType.ELECTRON is not BeamType.ION
    assert BeamType.ELECTRON != BeamType.ION
