# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The style sheet of a scroll area holding settings forms."""

FORM_STYLESHEET = """
    QWidget[dataclass_form="true"] QWidget[highlighted="true"] {
        border: 1px solid #346792;
        border-radius: 3px;
    }
"""
"""Frames the field under the mouse (its `highlighted` property) in every form inside."""
