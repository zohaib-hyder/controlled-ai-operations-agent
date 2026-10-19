"""Create or explicitly reset only the dedicated, marked northstar_demo database."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
MARKER = "northstar-phase12-synthetic-demo-v1"


def validate_target(url, app_env, provider):
    parsed = make_url(url)
    if (
        parsed.drivername not in {"postgresql", "postgresql+psycopg"}
        or parsed.host not in {"localhost", "127.0.0.1"}
        or parsed.database != "northstar_demo"
        or app_env not in {"development", "test"}
        or provider != "mock"
        or parsed.query
    ):
        raise ValueError(
            "Only local northstar_demo in development/test mock mode is permitted"
        )
    return parsed


def verify_demo_runtime():
    """Refuse fixture faults unless the actual isolated backend is synthetic mock."""
    subprocess.run(
        [
            "docker",
            "compose",
            "-p",
            "northstar-release12",
            "-f",
            "docker-compose.yml",
            "-f",
            "infra/docker/release.compose.yml",
            "exec",
            "-T",
            "backend",
            "python",
            "-c",
            "from app.core.config import get_settings; from sqlalchemy.engine import make_url; s=get_settings(); assert s.ai_provider == 'mock' and s.app_env == 'development' and make_url(s.database_url).database == 'northstar_demo'",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=15,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--initialize",
        action="store_true",
        help="Create a new database; refuse any existing target",
    )
    parser.add_argument(
        "--confirm-synthetic-reset",
        action="store_true",
        help="WARNING: delete ALL data in the previously marked demo database",
    )
    args = parser.parse_args()
    if args.initialize == args.confirm_synthetic_reset:
        parser.error("Choose --initialize OR --confirm-synthetic-reset")
    values = {
        k: v
        for k, v in {**dotenv_values(ROOT / ".env"), **os.environ}.items()
        if v is not None
    }
    try:
        target = validate_target(
            values.get("DATABASE_URL", ""),
            values.get("APP_ENV", "development"),
            values.get("AI_PROVIDER", "mock"),
        )
    except (ValueError, TypeError):
        parser.error(
            "Refusing target: explicitly set DATABASE_URL to loopback northstar_demo; mock development/test only"
        )

    def connect(database):
        return psycopg.connect(
            host=target.host,
            port=target.port or 5432,
            dbname=database,
            user=target.username,
            password=target.password,
            autocommit=True,
        )

    with connect("postgres") as admin:
        admin.execute("SELECT pg_advisory_lock(411071212)")
        exists = admin.execute(
            "SELECT 1 FROM pg_database WHERE datname=%s", (target.database,)
        ).fetchone()
        if args.initialize:
            if exists:
                raise SystemExit(
                    "Refusing existing database; initialization is never a reset"
                )
            admin.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target.database))
            )
        else:
            if not exists:
                raise SystemExit("No marked demo database exists")
            with connect(target.database) as connection:
                marker = connection.execute(
                    "SELECT value FROM public.northstar_demo_marker"
                ).fetchall()
                if marker != [(MARKER,)]:
                    raise SystemExit("Refusing unmarked database")
                # Refuse live services/concurrent clients before destructive reset.
                active = connection.execute(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()"
                ).fetchone()[0]
                if active:
                    raise SystemExit(
                        "Stop all clients connected to northstar_demo before reset"
                    )
                print(
                    "WARNING: deleting all data in marked local northstar_demo",
                    flush=True,
                )
                connection.execute("DROP SCHEMA public CASCADE")
                connection.execute("CREATE SCHEMA public")
        environment = {
            **values,
            "DATABASE_URL": target.render_as_string(hide_password=False),
        }
        for command in (
            [str(ROOT / "backend/.venv/bin/alembic"), "upgrade", "head"],
            [sys.executable, "-m", "app.db.seed_auth"],
        ):
            subprocess.run(command, cwd=ROOT / "backend", env=environment, check=True)
        with connect(target.database) as connection:
            connection.execute(
                "CREATE TABLE public.northstar_demo_marker (value text PRIMARY KEY)"
            )
            connection.execute(
                "INSERT INTO public.northstar_demo_marker VALUES (%s)", (MARKER,)
            )
    print(
        "Dedicated synthetic demo database ready; existing northstar database untouched"
    )


if __name__ == "__main__":
    main()
