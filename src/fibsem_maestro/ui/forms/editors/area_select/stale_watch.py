# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Re-checks an area selector's image for staleness whenever the settings change."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fibsem_maestro.settings.reactive import ChangePath, ReactiveNode
    from fibsem_maestro.ui.forms.editors.area_select.widget import AreaSelectWidget


class StaleImageWatch:
    """
    A settings hook calling `AreaSelectWidget.check_stale` on every change.

    The hook is registered on construction and removed by `release`, which
    must be called when the area selector is destroyed or its form disposed;
    `attach` arranges the former.

    Args:
        area: The area selector to check.
        settings: The live settings whose changes may move the acquisition offset.
    """

    def __init__(self, area: AreaSelectWidget, settings: ReactiveNode) -> None:
        self._area: AreaSelectWidget | None = area
        self._unsubscribe = settings.on_change_at(self)

    @classmethod
    def attach(cls, area: AreaSelectWidget, settings: ReactiveNode) -> StaleImageWatch:
        """
        Watch `settings` for `area` until the area selector is destroyed.

        Args:
            area: The area selector to check.
            settings: The live settings to watch.

        Returns:
            The watch; call `release` to stop it earlier.
        """
        watch = cls(area, settings)
        area.destroyed.connect(watch.release)
        return watch

    def release(self, *_: object) -> None:
        """Remove the settings hook and stop touching the area selector. Idempotent."""
        self._area = None
        self._unsubscribe()

    def __call__(self, path: ChangePath) -> None:
        _ = path
        if self._area is not None:
            self._area.check_stale()
