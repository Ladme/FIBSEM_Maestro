# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from fibsem_maestro.gui.form_builder.widgets.area_select.widget import AreaSelectWidget
from fibsem_maestro.settings.reactive import ChangePath


class StaleImageWatch:
    """
    Re-checks an area selector's image for staleness on every settings change.

    Settings hooks cannot be removed, so the watch is deactivated when the
    widget is destroyed instead.

    Args:
        area: The area selector to check.
    """

    def __init__(self, area: AreaSelectWidget) -> None:
        self._area = area
        self._active = True

    def deactivate(self, *_: object) -> None:
        """Stop checking a widget that is gone."""
        self._active = False

    def __call__(self, path: ChangePath) -> None:
        _ = path
        if self._active:
            self._area.check_stale()
