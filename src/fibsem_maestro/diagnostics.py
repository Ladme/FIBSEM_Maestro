# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

"""
Temporary file.
"""

import json
import platform
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from autoscript_sdb_microscope_client.sdb_microscope_client import SdbMicroscopeClient


def _safe(getter: Any) -> Any:
    try:
        value = getter()
    except Exception as error:
        return f"<unavailable: {type(error).__name__}: {error}>"
    return (
        value if isinstance(value, (int, float, str, bool, type(None))) else repr(value)
    )


def _describe_array(array: np.ndarray) -> dict[str, Any]:
    flat = array.reshape(-1)
    return {
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "strides": list(array.strides),
        "c_contiguous": bool(array.flags["C_CONTIGUOUS"]),
        "owns_data": bool(array.flags["OWNDATA"]),
        "min": int(flat.min()),
        "max": int(flat.max()),
        "mean": round(float(flat.mean()), 3),
        "distinct_levels": int(len(np.unique(flat))),
        "percentiles": {
            str(p): round(float(v), 2)
            for p, v in zip(
                (0.1, 1, 50, 99, 99.9), np.percentile(flat, [0.1, 1, 50, 99, 99.9])
            )
        },
    }


def _microscope_state(microscope: SdbMicroscopeClient) -> dict[str, Any]:
    imaging = microscope.imaging
    beams = microscope.beams
    return {
        "client_version": _safe(lambda: microscope.service.system.version),
        "server_version": _safe(lambda: microscope.service.autoscript.server.version),
        "active_view": _safe(imaging.get_active_view),
        "active_device": _safe(imaging.get_active_device),
        "scanning_filter_type": _safe(lambda: imaging.scanning_filter.type),
        "scanning_filter_frames": _safe(
            lambda: imaging.scanning_filter.number_of_frames
        ),
        "eb_resolution": _safe(lambda: beams.electron_beam.scanning.resolution.value),
        "eb_dwell_time": _safe(lambda: beams.electron_beam.scanning.dwell_time.value),
        "eb_bit_depth": _safe(lambda: beams.electron_beam.scanning.bit_depth),
        "eb_scan_mode": _safe(lambda: beams.electron_beam.scanning.mode.value),
        "detector_type": _safe(lambda: microscope.detector.type.value),
        "detector_mode": _safe(lambda: microscope.detector.mode.value),
        "detector_brightness": _safe(lambda: microscope.detector.brightness.value),
        "detector_contrast": _safe(lambda: microscope.detector.contrast.value),
    }


def _widget_state(widget: Any) -> dict[str, Any]:
    viewer = widget._viewer
    return {
        "platform": platform.platform(),
        "expanded": bool(widget._expanded),
        "image_size": list(widget._image_size) if widget._image_size else None,
        "viewer_size": [viewer.width(), viewer.height()],
        "viewport_size": [viewer.viewport().width(), viewer.viewport().height()],
        "device_pixel_ratio": float(viewer.devicePixelRatioF()),
        "view_scale_m11": float(viewer.transform().m11()),
        "view_scale_m22": float(viewer.transform().m22()),
        "tracked_zoom": float(viewer._zoom),
        "scene_rect": [
            widget._scene.sceneRect().width(),
            widget._scene.sceneRect().height(),
        ],
    }


def capture_diagnostics(
    microscope: SdbMicroscopeClient,
    widget: Any,
    out_dir: Path | str = "diagnostics",
    repeats: int = 3,
    also_grab_frame: bool = True,
) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = Path(out_dir) / stamp
    folder.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"timestamp": stamp}

    # the painted object
    try:
        widget._viewer.grab().save(str(folder / "rendered_viewport.png"))
        if widget._last_pixmap is not None:
            widget._last_pixmap.save(str(folder / "source_pixmap.png"))
        report["render_capture"] = "ok"
    except Exception as error:  # noqa: BLE001
        report["render_capture"] = f"failed: {error}"

    # the frame as Autoscript delivered it
    as_image = microscope.imaging.get_image()
    raw = np.asarray(as_image.data)
    np.save(folder / "raw_get_image.npy", raw)
    report["adorned_image"] = {
        "width": _safe(lambda: as_image.width),
        "height": _safe(lambda: as_image.height),
        "bit_depth": _safe(lambda: as_image.bit_depth),
        "encoding": _safe(lambda: as_image.encoding),
        "checksum": _safe(lambda: as_image.checksum),
    }
    report["raw_array"] = _describe_array(raw)

    # the array that reaches qt after to_8bit
    try:
        from fibsem_maestro.core.image import Image

        eight = np.asarray(Image(raw, pixel_size=1.0).to_8bit())
        np.save(folder / "converted_8bit.npy", eight)
        report["converted_array"] = _describe_array(eight)
    except Exception as error:  # noqa: BLE001
        report["converted_array"] = f"failed: {error}"

    # do successive grabs of the same scene differ?
    report["repeat_checksums"] = [
        _safe(lambda: microscope.imaging.get_image().checksum) for _ in range(repeats)
    ]

    # A/B against a freshly scanned frame
    if also_grab_frame:
        try:
            grabbed = microscope.imaging.grab_frame()
            grabbed_raw = np.asarray(grabbed.data)
            np.save(folder / "raw_grab_frame.npy", grabbed_raw)
            report["grab_frame"] = {
                "width": _safe(lambda: grabbed.width),
                "height": _safe(lambda: grabbed.height),
                "bit_depth": _safe(lambda: grabbed.bit_depth),
                "encoding": _safe(lambda: grabbed.encoding),
                "array": _describe_array(grabbed_raw),
            }
        except Exception as error:
            report["grab_frame"] = f"failed: {error}"

    report["microscope"] = _microscope_state(microscope)
    report["widget"] = _widget_state(widget)

    (folder / "report.json").write_text(json.dumps(report, indent=2, default=str))
    return folder
