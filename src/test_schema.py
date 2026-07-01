from fibsem_maestro.gui.new_form_builder.schema.schema import get_field_infos
from fibsem_maestro.settings.autofocus_settings import AutofocusSettings
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings

if __name__ == "__main__":
    for info in get_field_infos(ImagingSettings):
        print(">  ", info)
        print()
