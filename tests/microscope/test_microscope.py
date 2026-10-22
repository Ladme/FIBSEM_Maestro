from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.properties.global_properties import GlobalProperties


def test_set_properties_leaves_its_argument_unchanged(
    mock_microscope: Microscope,
) -> None:
    props = GlobalProperties(
        electron_beam=BeamProperties(
            beam_shift=BeamShift(10.0, 5.0), working_distance=4e6
        )
    )
    before = props.model_dump()

    mock_microscope.set_properties(props, None)

    assert props.model_dump() == before


def test_set_properties_still_applies_beam_shift(mock_microscope: Microscope) -> None:
    props = GlobalProperties(
        electron_beam=BeamProperties(beam_shift=BeamShift(10.0, 5.0))
    )
    mock_microscope.set_properties(props, None)
    assert mock_microscope.electron_beam.beam_shift == BeamShift(10.0, 5.0)
