# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

import faulthandler
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import TextIO

from PyQt6.QtCore import QMessageLogContext, QtMsgType, qInstallMessageHandler

_lock = threading.Lock()
_file: TextIO | None = None
_reported_stacks: set[tuple[str, str]] = set()


def install_crash_diagnostics(path: Path) -> None:
    """
    Route native faults, unhandled exceptions, and Qt messages to a file.

    Call once at start-up, before the `QApplication` is created. Installing an
    excepthook changes PyQt's behaviour: an exception raised inside a Qt
    callback (a `paint` override, a slot) is logged and the application keeps
    running, instead of PyQt calling `qFatal()` and aborting.

    Args:
        path: File to append to. It stays open for the lifetime of the process,
            because `faulthandler` writes to its file descriptor at crash time.
    """
    global _file
    path.parent.mkdir(parents=True, exist_ok=True)
    _file = path.open("a", encoding="utf-8", buffering=1)
    _write(f"=== session started {datetime.now().isoformat(timespec='seconds')} ===")

    faulthandler.enable(file=_file, all_threads=True)
    sys.excepthook = _on_unhandled_exception
    threading.excepthook = _on_unhandled_thread_exception
    qInstallMessageHandler(_on_qt_message)


def _write(text: str) -> None:
    """Append a block of text and flush it, so it survives an immediate crash."""
    if _file is None:
        return
    with _lock:
        _file.write(text.rstrip("\n") + "\n")
        _file.flush()


def _on_unhandled_exception(
    exc_type: type[BaseException],
    exc: BaseException,
    tb: TracebackType | None,
) -> None:
    """Log an exception that reached `sys.excepthook`, including Qt callbacks."""
    _write(
        f"Unhandled exception in thread {threading.current_thread().name!r}:\n"
        + "".join(traceback.format_exception(exc_type, exc, tb))
    )


def _on_unhandled_thread_exception(args: threading.ExceptHookArgs) -> None:
    """Log an exception that escaped a `threading.Thread`."""
    name = args.thread.name if args.thread is not None else "<unknown>"
    _write(
        f"Unhandled exception in thread {name!r}:\n"
        + "".join(
            traceback.format_exception(
                args.exc_type, args.exc_value, args.exc_traceback
            )
        )
    )


def _on_qt_message(
    mode: QtMsgType, context: QMessageLogContext, message: str | None
) -> None:
    """
    Log a Qt message; off the GUI thread, also log the Python call path.
    """
    _ = context
    thread = threading.current_thread()
    text = f"Qt {mode.name} in thread {thread.name!r}: {message}"

    if thread is not threading.main_thread():
        stack = "".join(traceback.format_stack()[:-1])
        key = (message or "", stack)
        with _lock:
            if key in _reported_stacks:
                return
            _reported_stacks.add(key)
        text += "\n" + stack

    _write(text)
