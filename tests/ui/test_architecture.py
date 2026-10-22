# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""
The architecture of the GUI, enforced.

Layers and what they must not import:

| Layer      | Package                          | Must not import                                   |
|------------|----------------------------------|---------------------------------------------------|
| backend    | fibsem_maestro (not ui, main.py) | fibsem_maestro.ui                                 |
| schema     | ui/schema                        | PyQt6, any other ui package                       |
| ports      | ui/ports.py                      | PyQt6.QtWidgets, PyQt6.QtGui, any other ui package |
| app        | ui/app                           | QtWidgets, QtGui, forms, views, widgets, actions_ui |
| forms      | ui/forms                         | app, views, widgets, actions_ui                   |
| widgets    | ui/widgets                       | app, actions_ui, views                            |
| actions_ui | ui/actions_ui                    | views                                             |

Views may import all of `ui`; `ui/composition.py` and `main.py` wire everything.

Signal rules: views and forms emit only their own signals (`self.<signal>.emit`), and
long-lived signals (of services and task handles) are connected to bound methods,
never to lambdas or partials, which Qt cannot disconnect when a widget dies.

Sources are parsed with `ast`, never imported; every file found is checked, so new
modules are covered automatically. Each checker is also tested on a synthetic source.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE_DIR = Path(__file__).resolve().parents[2] / "src" / "fibsem_maestro"
UI = "fibsem_maestro.ui"
QT_WIDGETS = ("PyQt6.QtWidgets", "PyQt6.QtGui")

LAYERS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    # layer: (forbidden import prefixes, allowed exceptions below them)
    "schema": (("PyQt6", UI), (f"{UI}.schema",)),
    "ports.py": ((*QT_WIDGETS, UI), (f"{UI}.ports",)),
    "app": (
        (
            *QT_WIDGETS,
            *(f"{UI}.{p}" for p in ("forms", "views", "widgets", "actions_ui")),
        ),
        (),
    ),
    "forms": (
        tuple(f"{UI}.{p}" for p in ("app", "views", "widgets", "actions_ui")),
        (),
    ),
    "widgets": (tuple(f"{UI}.{p}" for p in ("app", "actions_ui", "views")), ()),
    "actions_ui": ((f"{UI}.views",), ()),
}

SERVICE_HOLDERS = frozenset(
    {
        "session",
        "run",
        "policy",
        "readiness",
        "status",
        "tasks",
        "form_validity",
        "validity",
        "actions",
        "catalog",
        "preview_permission",
    }
)
"""Names under which views and forms hold long-lived signal sources (leading `_` ignored)."""

HANDLE_SIGNALS = frozenset({"succeeded", "failed"})
"""`TaskHandle` signals: also long-lived, the task may outlive the widget."""


def ui_files(*parts: str) -> list[Path]:
    """Python files at or under `ui/<parts>`."""
    target = PACKAGE_DIR / "ui" / Path(*parts)
    return [target] if target.is_file() else sorted(target.rglob("*.py"))


def backend_files() -> list[Path]:
    """Every module of the package outside `ui/`, except the entry point `main.py`."""
    return [
        path
        for path in sorted(PACKAGE_DIR.rglob("*.py"))
        if path != PACKAGE_DIR / "main.py"
        and not path.is_relative_to(PACKAGE_DIR / "ui")
    ]


def module_name(path: Path) -> str:
    """The dotted module name of a file of the package."""
    parts = list(path.relative_to(PACKAGE_DIR.parent).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def import_violations(
    path: Path, forbidden: tuple[str, ...], allowed: tuple[str, ...] = ()
) -> list[str]:
    """The forbidden imports of a source file, as `file:line: imports <name>`."""
    found = forbidden_imports(
        path.read_text(encoding="utf-8"),
        module_name(path),
        forbidden,
        allowed,
        is_package=path.name == "__init__.py",
    )
    return [f"{location(path, node)}: imports {name}" for node, name in found]


def location(path: Path, node: ast.AST) -> str:
    """`file:line` of a node, relative to the repository."""
    return f"{path.relative_to(PACKAGE_DIR.parents[1])}:{getattr(node, 'lineno', 0)}"


def imports(
    source: str, module: str, is_package: bool = False
) -> list[tuple[ast.AST, str]]:
    """
    Every dotted name a module imports, wherever the import is (functions, TYPE_CHECKING).

    `from a import b` yields `a.b`; relative imports are resolved against `module`
    (a package's `__init__` if `is_package`).
    """
    found: list[tuple[ast.AST, str]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.extend((node, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                package = module.split(".")[: None if is_package else -1]
                package = package[: len(package) - node.level + 1]
                base = ".".join([*package, base] if base else package)
            found.extend(
                (node, base if alias.name == "*" else f"{base}.{alias.name}")
                for alias in node.names
            )
    return found


def forbidden_imports(
    source: str,
    module: str,
    forbidden: tuple[str, ...],
    allowed: tuple[str, ...] = (),
    is_package: bool = False,
) -> list[tuple[ast.AST, str]]:
    """The imports of `source` below a forbidden prefix and not below an allowed one."""

    def within(name: str, prefixes: tuple[str, ...]) -> bool:
        return any(name == p or name.startswith(f"{p}.") for p in prefixes)

    return [
        (node, name)
        for node, name in imports(source, module, is_package)
        if within(name, forbidden) and not within(name, allowed)
    ]


def foreign_emits(source: str) -> list[ast.Call]:
    """Every `.emit(...)` on something other than an attribute of `self`."""
    return [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "emit"
        and not (
            isinstance(signal := node.func.value, ast.Attribute)
            and isinstance(signal.value, ast.Name)
            and signal.value.id == "self"
        )
    ]


def unsafe_connects(source: str) -> list[ast.Call]:
    """Every connection of a long-lived signal to a lambda or a `partial(...)`."""

    def long_lived(signal: ast.expr) -> bool:
        if not isinstance(signal, ast.Attribute):
            return False
        holder = signal.value
        name = (
            holder.attr
            if isinstance(holder, ast.Attribute)
            else getattr(holder, "id", "")
        )
        return signal.attr in HANDLE_SIGNALS or name.lstrip("_") in SERVICE_HOLDERS

    def unsafe(slot: ast.expr) -> bool:
        if isinstance(slot, ast.Lambda):
            return True
        func = slot.func if isinstance(slot, ast.Call) else None
        return (isinstance(func, ast.Name) and func.id == "partial") or (
            isinstance(func, ast.Attribute) and func.attr == "partial"
        )

    return [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "connect"
        and long_lived(node.func.value)
        and any(unsafe(arg) for arg in [*node.args, *(k.value for k in node.keywords)])
    ]


def report(rule: str, violations: list[str]) -> str:
    return f"{rule}:\n  " + "\n  ".join(violations)


def test_architecture_finds_the_sources() -> None:
    # guards against every other test passing vacuously after a move
    for layer in (*LAYERS, "views"):
        assert ui_files(layer), f"no sources found for ui/{layer}"
    assert len(backend_files()) > 50


@pytest.mark.parametrize("layer", list(LAYERS))
def test_layer_imports_follow_the_layer_table(layer: str) -> None:
    forbidden, allowed = LAYERS[layer]
    violations = [
        v
        for path in ui_files(layer)
        for v in import_violations(path, forbidden, allowed)
    ]
    assert not violations, report(f"ui/{layer} must not import {forbidden}", violations)


def test_backend_imports_no_ui() -> None:
    violations = [v for path in backend_files() for v in import_violations(path, (UI,))]
    assert not violations, report("the backend must not import the GUI", violations)


def test_views_and_forms_emit_only_own_signals() -> None:
    violations = [
        f"{location(path, node)}: {ast.unparse(node)}"
        for path in ui_files("views") + ui_files("forms")
        for node in foreign_emits(path.read_text(encoding="utf-8"))
    ]
    assert not violations, report(
        "only the owner emits a signal (self.<signal>.emit)", violations
    )


def test_long_lived_signals_connect_to_bound_methods() -> None:
    files = [
        path
        for layer in ("views", "forms", "widgets", "actions_ui")
        for path in ui_files(layer)
    ]
    violations = [
        f"{location(path, node)}: {ast.unparse(node)}"
        for path in files
        for node in unsafe_connects(path.read_text(encoding="utf-8"))
    ]
    assert not violations, report(
        "service and task-handle signals connect to bound methods (rule 9)", violations
    )


@pytest.mark.parametrize(
    ("source", "name"),
    [
        ("import PyQt6.QtWidgets as qw\n", "PyQt6.QtWidgets"),
        ("from PyQt6 import QtGui\n", "PyQt6.QtGui"),
        ("from PyQt6.QtWidgets import *\n", "PyQt6.QtWidgets"),
        (
            "if TYPE_CHECKING:\n    from PyQt6.QtWidgets import QWidget\n",
            "PyQt6.QtWidgets.QWidget",
        ),
        ("def f():\n    from ..views import top_bar\n", f"{UI}.views.top_bar"),
        ("from ...ui.forms.builder import Form\n", f"{UI}.forms.builder.Form"),
    ],
)
def test_import_checker_catches_forbidden_import(source: str, name: str) -> None:
    found = forbidden_imports(source, f"{UI}.app.module", LAYERS["app"][0])
    assert [n for _, n in found] == [name]


@pytest.mark.parametrize(
    "source",
    [
        "from PyQt6.QtCore import QObject\n",
        "from .. import schema, ports\n",
        "import fibsem_maestro.ui_tools\n",  # a prefix only matches whole dotted parts
    ],
)
def test_import_checker_allows_permitted_import(source: str) -> None:
    assert not forbidden_imports(source, f"{UI}.app.module", LAYERS["app"][0])


def test_import_checker_honours_allowed_exceptions() -> None:
    source = "from fibsem_maestro.ui.schema.choices import choices_for\n"
    assert not forbidden_imports(source, f"{UI}.schema.audit", *LAYERS["schema"])
    assert forbidden_imports(source, f"{UI}.ports", *LAYERS["ports.py"])


def test_import_checker_resolves_relative_imports_of_packages() -> None:
    found = forbidden_imports(
        "from .views import x\n", UI, (f"{UI}.views",), is_package=True
    )
    assert [n for _, n in found] == [f"{UI}.views.x"]


@pytest.mark.parametrize(
    "source",
    [
        "self._session.structure_changed.emit()\n",
        "session.rules_changed.emit()\n",
        "self.handle().succeeded.emit(1)\n",
    ],
)
def test_emit_checker_catches_foreign_signal(source: str) -> None:
    assert len(foreign_emits(source)) == 1


def test_emit_checker_allows_own_signal() -> None:
    assert not foreign_emits("self.changed.emit()\nself._refused.emit(1, 2)\n")


@pytest.mark.parametrize(
    "source",
    [
        "self._session.structure_changed.connect(lambda: self.refresh())\n",
        "run.state_changed.connect(partial(self.on_state, 1))\n",
        "self._policy.changed.connect(functools.partial(self.f, 1))\n",
        "self._tasks.busy_changed.connect(slot=lambda busy: None)\n",
        "context.catalog.action_renamed.connect(lambda a, n: None)\n",
        "handle.failed.connect(lambda error: self.show(error))\n",
    ],
)
def test_connect_checker_catches_lambda_or_partial(source: str) -> None:
    assert len(unsafe_connects(source)) == 1


@pytest.mark.parametrize(
    "source",
    [
        "self._session.structure_changed.connect(self._on_structure_changed)\n",
        "handle.succeeded.connect(self._on_image)\n",
        # signals of the widget's own children die with it
        "self._button.clicked.connect(lambda: self.close())\n",
    ],
)
def test_connect_checker_allows_bound_method_or_own_widget(source: str) -> None:
    assert not unsafe_connects(source)


def test_violation_location_names_file_and_line() -> None:
    ((node, _),) = forbidden_imports(
        "import os\n\nimport PyQt6.QtGui\n", "m", QT_WIDGETS
    )
    path = PACKAGE_DIR / "ui" / "app" / "session.py"
    assert location(path, node) == "src/fibsem_maestro/ui/app/session.py:3"
