"""Simplified database stub (no SQLAlchemy dependency)."""

DATABASE_URL = "sqlite:///./app.db"


class Session:
    """Stub session for demonstration."""

    def __enter__(self) -> "Session":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    @classmethod
    def begin(cls) -> "Session":
        return cls()


engine = {"url": DATABASE_URL}
