from __future__ import annotations

import atexit
import datetime as dt
import logging
import os
import queue
import sys
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is present in normal installs
    def load_dotenv(*args, **kwargs):
        return False


load_dotenv()

LOGGER_NAME = "app_logger"
DEFAULT_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
DEFAULT_LOG_FILE = "app.log"
DEFAULT_LOG_FILE_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_LOG_RETENTION_DAYS = 30
DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_log_queue: queue.Queue[logging.LogRecord] | None = None
_queue_listener: QueueListener | None = None
_listener_handlers: list[logging.Handler] = []
_configured = False


def _resolve_level(value: str | None, default: str) -> int:
    level_name = (value or default).upper()

    if level_name.isdigit():
        return int(level_name)

    return getattr(logging, level_name, getattr(logging, default.upper()))


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def _build_formatter() -> logging.Formatter:
    return logging.Formatter(
        os.getenv("LOG_FORMAT", DEFAULT_LOG_FORMAT),
        os.getenv("LOG_DATE_FORMAT", DEFAULT_DATE_FORMAT),
    )


def _get_log_retention_days() -> int:
    if os.getenv("LOG_RETENTION_DAYS"):
        return _get_int("LOG_RETENTION_DAYS", DEFAULT_LOG_RETENTION_DAYS)

    return _get_int("LOG_BACKUP_COUNT", DEFAULT_LOG_RETENTION_DAYS)


class DailyFileHandler(logging.Handler):
    def __init__(
        self,
        log_dir: Path,
        file_name: str,
        date_format: str,
        backup_count: int,
        encoding: str = "utf-8",
    ) -> None:
        super().__init__()
        self.log_dir = log_dir
        self.file_name = Path(file_name)
        self.date_format = date_format
        self.backup_count = backup_count
        self.encoding = encoding
        self._current_date = ""
        self._current_handler: logging.FileHandler | None = None
        self._last_cleanup_date = ""

    def setFormatter(self, fmt: logging.Formatter | None) -> None:  # noqa: N802
        super().setFormatter(fmt)

        if self._current_handler is not None:
            self._current_handler.setFormatter(fmt)

    def setLevel(self, level: int | str) -> None:  # noqa: N802
        super().setLevel(level)

        if self._current_handler is not None:
            self._current_handler.setLevel(level)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._ensure_current_handler()

            if self._current_handler is not None:
                self._current_handler.emit(record)
        except Exception:
            self.handleError(record)

    def flush(self) -> None:
        if self._current_handler is not None:
            self._current_handler.flush()

    def close(self) -> None:
        try:
            self._close_current_handler()
        finally:
            super().close()

    def _ensure_current_handler(self) -> None:
        date_text = dt.datetime.now().strftime(self.date_format)

        if self._current_handler is not None and self._current_date == date_text:
            return

        self._close_current_handler()

        log_path = self._get_log_path(date_text)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        self._current_handler = logging.FileHandler(
            log_path,
            encoding=self.encoding,
            delay=True,
        )
        self._current_handler.setLevel(self.level)

        if self.formatter is not None:
            self._current_handler.setFormatter(self.formatter)

        self._current_date = date_text

        if self._last_cleanup_date != date_text:
            self._cleanup_old_logs()
            self._last_cleanup_date = date_text

    def _close_current_handler(self) -> None:
        handler = self._current_handler
        self._current_handler = None

        if handler is not None:
            handler.flush()
            handler.close()

    def _get_log_path(self, date_text: str) -> Path:
        log_parent = self.log_dir / self.file_name.parent
        dated_name = f"{self.file_name.stem}-{date_text}{self.file_name.suffix}"
        return log_parent / dated_name

    def _cleanup_old_logs(self) -> None:
        if self.backup_count <= 0:
            return

        log_parent = self.log_dir / self.file_name.parent
        pattern = f"{self.file_name.stem}-*{self.file_name.suffix}"

        try:
            log_files = sorted(
                log_parent.glob(pattern),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
        except OSError:
            return

        for log_file in log_files[self.backup_count:]:
            try:
                log_file.unlink()
            except OSError:
                pass


def _build_handlers(formatter: logging.Formatter) -> list[logging.Handler]:
    handlers: list[logging.Handler] = []

    if _get_bool("LOG_TO_CONSOLE", True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(_resolve_level(os.getenv("LOG_CONSOLE_LEVEL"), "INFO"))
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    if _get_bool("LOG_TO_FILE", True):
        try:
            log_dir = Path(os.getenv("LOG_DIR", str(DEFAULT_LOG_DIR))).expanduser()
            log_dir.mkdir(parents=True, exist_ok=True)

            file_handler = DailyFileHandler(
                log_dir=log_dir,
                file_name=os.getenv("LOG_FILE", DEFAULT_LOG_FILE),
                date_format=os.getenv(
                    "LOG_FILE_DATE_FORMAT",
                    DEFAULT_LOG_FILE_DATE_FORMAT,
                ),
                backup_count=_get_log_retention_days(),
            )
            file_handler.setLevel(_resolve_level(os.getenv("LOG_FILE_LEVEL"), "DEBUG"))
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except OSError as exc:
            print(f"Failed to set up file logging: {exc}", file=sys.stderr)

    return handlers


def setup_logging(force: bool = False) -> logging.Logger:
    global _configured, _log_queue, _queue_listener, _listener_handlers

    app_logger = logging.getLogger(LOGGER_NAME)

    if _configured and not force:
        return app_logger

    shutdown_logging()

    app_logger = logging.getLogger(LOGGER_NAME)
    app_logger.disabled = False
    app_logger.setLevel(_resolve_level(os.getenv("LOG_LEVEL"), "DEBUG"))
    app_logger.handlers.clear()
    app_logger.propagate = False

    handlers = _build_handlers(_build_formatter())

    if handlers:
        _log_queue = queue.Queue(-1)
        queue_handler = QueueHandler(_log_queue)
        queue_handler.setLevel(logging.NOTSET)
        app_logger.addHandler(queue_handler)

        _queue_listener = QueueListener(
            _log_queue,
            *handlers,
            respect_handler_level=True,
        )
        _queue_listener.start()
        _listener_handlers = handlers
    else:
        app_logger.addHandler(logging.NullHandler())
        _log_queue = None
        _queue_listener = None
        _listener_handlers = []

    _configured = True
    return app_logger


def get_logger(name: str | None = None) -> logging.Logger:
    setup_logging()

    if not name:
        return logging.getLogger(LOGGER_NAME)

    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def shutdown_logging() -> None:
    global _configured, _log_queue, _queue_listener, _listener_handlers

    listener = _queue_listener
    _queue_listener = None

    if listener is not None:
        try:
            listener.stop()
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            print(f"Failed to stop log listener: {exc}", file=sys.stderr)

    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    for handler in _listener_handlers:
        handler.close()

    _listener_handlers = []
    _log_queue = None
    _configured = False


app_logger = setup_logging()
atexit.register(shutdown_logging)
