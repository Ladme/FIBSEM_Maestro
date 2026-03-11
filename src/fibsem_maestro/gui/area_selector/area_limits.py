# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections import Counter

from fibsem_maestro.gui.area_selector.area_type import AreaType
from fibsem_maestro.gui.area_selector.selected_area import SelectedArea


class AreaLimits:
    def __init__(self):
        self._area_limits: dict[AreaType, int] = {}

    def add_limit(self, area_type: AreaType, max_areas: int) -> None:
        self._area_limits[area_type] = max_areas

    def get_limit(self, area_type: AreaType) -> int:
        return self._area_limits.get(area_type) or 0

    def get_remaining(self, area_type: AreaType, current: int) -> int:
        return self.get_limit(area_type) - current

    def get_available(self, areas: list[SelectedArea]) -> list[AreaType]:
        counts = Counter([area.type for area in areas])

        return [
            area_type
            for area_type in self._area_limits
            if self.get_remaining(area_type, counts[area_type]) > 0
        ]
