# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from fibsem_maestro.core.area import PixelArea
from fibsem_maestro.gui.area_selector.area_state import AreaState
from fibsem_maestro.gui.area_selector.area_type import AreaType


class SelectedArea(PixelArea):
    type: AreaType
    state: AreaState
    padding: tuple[int, int]

    @property
    def color(self) -> str:
        match self.state:
            case AreaState.OBSOLETE:
                return "#828282"
            case AreaState.ACTIVE:
                match self.type:
                    case AreaType.SCANNING:
                        return "#00E5FF"
                    case AreaType.TEMPLATE:
                        return "#FFD600"
                    case AreaType.FIDUCIAL:
                        return "#FF40FF"
                    case AreaType.MILLING:
                        return "#76FF03"
            case AreaState.FINALIZED:
                match self.type:
                    case AreaType.SCANNING:
                        return "#0d10d4"
                    case AreaType.TEMPLATE:
                        return "#d15700"
                    case AreaType.FIDUCIAL:
                        return "#7B1FA2"
                    case AreaType.MILLING:
                        return "#167802"

    @property
    def label(self) -> str:
        match self.type:
            case AreaType.SCANNING:
                return "scanning area"
            case AreaType.TEMPLATE:
                return "template area"
            case AreaType.FIDUCIAL:
                return "fiducial"
            case AreaType.MILLING:
                return "milling area"

    def render(self) -> str:
        return (
            f'<rect x="{self.origin.x}" y="{self.origin.y}" width="{self.width}" height="{self.height}" '
            f'fill="{self.color}" fill-opacity="0.1" stroke="{self.color}" stroke-width="5" />'
            f'<text x="{self.origin.x + self.width // 2}" y="{self.origin.y + 20}" text-anchor="middle" '
            f'dominant-baseline="middle" fill="{self.color}" font-size="12">'
            f"{self.label}</text>"
        )
