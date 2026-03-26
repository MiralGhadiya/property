from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.script.revision import ResolutionError
from alembic.util.exc import CommandError
from sqlalchemy import inspect, text

import app.models  # noqa: F401  Ensures all models are registered on Base.metadata.
from app.database.db import Base, engine, get_database_url
from app.utils.logger_config import app_logger as logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"
APP_TABLE_NAMES = frozenset(Base.metadata.tables.keys())


def build_alembic_config() -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", get_database_url())
    return config


def get_single_head_revision(script_directory: ScriptDirectory) -> str:
    heads = script_directory.get_heads()

    if len(heads) != 1:
        raise RuntimeError(
            "Expected exactly one Alembic head revision, "
            f"found {len(heads)}: {heads}"
        )

    return heads[0]


def get_current_revisions(connection) -> tuple[str, ...]:
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names(schema="public"))

    if "alembic_version" not in table_names:
        return ()

    revisions = connection.execute(
        text("SELECT version_num FROM alembic_version ORDER BY version_num")
    ).scalars().all()

    return tuple(revisions)


def get_existing_app_tables(connection) -> set[str]:
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names(schema="public"))
    return table_names.intersection(APP_TABLE_NAMES)


def is_known_revision(
    script_directory: ScriptDirectory,
    revision: str,
) -> bool:
    try:
        return script_directory.get_revision(revision) is not None
    except (CommandError, ResolutionError):
        return False


def get_schema_diffs(connection) -> list:
    migration_context = MigrationContext.configure(
        connection,
        opts={"compare_type": True, "target_metadata": Base.metadata},
    )
    return compare_metadata(migration_context, Base.metadata)


def format_diffs(diffs: list, limit: int = 5) -> str:
    preview = [str(diff) for diff in diffs[:limit]]

    if len(diffs) > limit:
        preview.append(f"... and {len(diffs) - limit} more")

    return "; ".join(preview)


def rewrite_alembic_version(connection, head_revision: str) -> None:
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL PRIMARY KEY
            )
            """
        )
    )
    connection.execute(text("DELETE FROM alembic_version"))
    connection.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:head_revision)"),
        {"head_revision": head_revision},
    )


def reconcile_version_table_if_needed(
    script_directory: ScriptDirectory,
    head_revision: str,
) -> bool:
    with engine.begin() as connection:
        existing_app_tables = get_existing_app_tables(connection)
        current_revisions = get_current_revisions(connection)

        if not existing_app_tables:
            return False

        unknown_revisions = tuple(
            revision
            for revision in current_revisions
            if not is_known_revision(script_directory, revision)
        )

        needs_reconciliation = bool(unknown_revisions) or not current_revisions

        if not needs_reconciliation:
            return False

        logger.warning(
            "Detected schema with %s existing application tables and "
            "%sAlembic revision metadata. Validating live schema before repair.",
            len(existing_app_tables),
            "unknown " if unknown_revisions else "missing ",
        )

        diffs = get_schema_diffs(connection)

        if diffs:
            current_state = (
                f"unknown revision(s) {unknown_revisions}"
                if unknown_revisions
                else "missing alembic_version rows"
            )
            raise RuntimeError(
                "Database schema cannot be auto-reconciled because the live "
                f"schema differs from the current SQLAlchemy metadata while "
                f"the database reports {current_state}. "
                f"Schema diffs: {format_diffs(diffs)}"
            )

        rewrite_alembic_version(connection, head_revision)

        if unknown_revisions:
            logger.warning(
                "Rewrote alembic_version from orphaned revision(s) %s to %s "
                "after confirming the live schema matches current metadata.",
                ", ".join(unknown_revisions),
                head_revision,
            )
        else:
            logger.warning(
                "Stamped existing schema to Alembic head %s after confirming "
                "the live schema matches current metadata.",
                head_revision,
            )

        return True


def run_migrations() -> None:
    config = build_alembic_config()
    script_directory = ScriptDirectory.from_config(config)
    head_revision = get_single_head_revision(script_directory)

    reconcile_version_table_if_needed(script_directory, head_revision)

    logger.info("Running Alembic upgrade to head revision %s", head_revision)
    command.upgrade(config, "head")
    logger.info("Alembic migrations completed successfully")


if __name__ == "__main__":
    run_migrations()
