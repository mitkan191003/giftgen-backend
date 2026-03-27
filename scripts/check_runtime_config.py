from __future__ import annotations

def main() -> int:
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.exc import ArgumentError
        from sqlalchemy.engine import make_url

        from app.core.config import Settings
    except ModuleNotFoundError as exc:
        missing = exc.name or "required dependency"
        print(
            f"Missing Python dependency: {missing}. Install backend dependencies first, "
            "for example with `uv sync` or `pip install -e .` from the backend directory."
        )
        return 1

    settings = Settings()

    try:
        parsed = make_url(settings.database_url)
        engine = create_engine(settings.database_url)
        engine.dispose()
    except ArgumentError as exc:
        print("Runtime config is invalid.")
        if settings.database_url.startswith("REPLACE_"):
            print(
                "DATABASE_URL is still set to a placeholder value. "
                "Either unset it to use the default sqlite URL, or set DATABASE_SECRET_ID "
                "and DATABASE_ENDPOINT to validate the deployed AWS runtime path."
            )
        else:
            print(
                "Resolved DATABASE_URL could not be parsed. "
                "Check DATABASE_URL or the DATABASE_SECRET_ID / DATABASE_ENDPOINT values."
            )
        print(f"SQLAlchemy error: {exc}")
        return 1

    print("Runtime config parsed successfully.")
    print(f"Database dialect: {parsed.drivername}")
    print(f"Database host: {parsed.host}")
    print(f"Database port: {parsed.port}")
    print(f"Database name: {parsed.database}")

    print("SQLAlchemy engine creation succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
