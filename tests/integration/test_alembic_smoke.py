"""
Integration smoke test for Alembic migrations.

Demonstrates that the project's actual async migration configuration:
1. Starts cleanly with async engine configuration in alembic/env.py.
2. Executes `upgrade head`, creating new tables and recording the revision.
3. Records the exact revision in the `alembic_version` table.
4. Executes `downgrade base`, cleanly rolling back the schema changes.
5. Leaves no temporary revisions or test databases behind in the repository.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

_REVISION_ID = "smoke_test_001"

_SMOKE_MIGRATION_SOURCE = f'''"""smoke test revision
Revision ID: {_REVISION_ID}
Revises:
Create Date: 2026-11-16
"""
from alembic import op
import sqlalchemy as sa

revision = "{_REVISION_ID}"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "smoke_test_table",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("description", sa.String(50)),
    )


def downgrade() -> None:
    op.drop_table("smoke_test_table")
'''


@pytest.mark.asyncio
async def test_alembic_upgrade_and_downgrade_cycle(tmp_path: Path) -> None:
    """Run an isolated upgrade head -> verify table -> downgrade base -> verify dropped cycle."""
    project_root = Path(__file__).resolve().parent.parent.parent
    alembic_ini = project_root / "backend" / "alembic.ini"
    smoke_versions_dir = tmp_path / "versions"
    smoke_versions_dir.mkdir(parents=True, exist_ok=True)
    temp_rev_file = smoke_versions_dir / f"{_REVISION_ID}_test.py"

    temp_db_file = tmp_path / "alembic_smoke.db"
    db_url = f"sqlite+aiosqlite:///{temp_db_file.absolute()}"

    # Write temporary migration revision
    temp_rev_file.write_text(_SMOKE_MIGRATION_SOURCE, encoding="utf-8")

    # Point Alembic configuration to temporary database and migration environment
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.set_main_option("script_location", str((project_root / "backend" / "alembic").absolute()))
    cfg.set_main_option("version_locations", str(smoke_versions_dir.absolute()))

    # Ensure environment picks up the isolated URL
    old_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = db_url

    try:
        # 1. Run upgrade head
        await asyncio.to_thread(command.upgrade, cfg, "head")

        # 2. Verify table exists and version is recorded
        verify_engine = create_async_engine(db_url)
        async with verify_engine.connect() as conn:
            tables_res = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in tables_res.fetchall()]
            assert "smoke_test_table" in tables, "smoke_test_table was not created!"
            assert "alembic_version" in tables, "alembic_version table was not created!"

            ver_res = await conn.execute(text("SELECT version_num FROM alembic_version"))
            recorded_ver = ver_res.scalar()
            assert recorded_ver == _REVISION_ID, f"Expected {_REVISION_ID}, got {recorded_ver}"
        await verify_engine.dispose()

        # 3. Run downgrade base
        await asyncio.to_thread(command.downgrade, cfg, "base")

        # 4. Verify table was removed
        async with verify_engine.connect() as conn:
            tables_res = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in tables_res.fetchall()]
            assert "smoke_test_table" not in tables, "smoke_test_table was not dropped!"
        await verify_engine.dispose()

    finally:
        # Clean up temporary revision file and restore environment
        if temp_rev_file.exists():
            temp_rev_file.unlink()
        if old_db_url is not None:
            os.environ["DATABASE_URL"] = old_db_url
        else:
            os.environ.pop("DATABASE_URL", None)
