# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from fibsem_maestro.logging.text.text_logger import TextLogger


class InMemoryTextLogger(TextLogger):
    """Simple logger that records messages in memory."""

    def __init__(self) -> None:
        self.debugs: list[str] = []
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def derive(self, name: str) -> "InMemoryTextLogger":
        _ = name
        return InMemoryTextLogger()

    def debug(self, msg: str) -> None:
        self.debugs.append(msg)

    def info(self, msg: str) -> None:
        self.infos.append(msg)

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)
