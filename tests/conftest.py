import os

# Settings are read when app.config is first imported, so the variables have
# to exist before any test module imports the app. Nothing here connects:
# SQLAlchemy only opens a connection on first use.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@127.0.0.1:5999/test")
