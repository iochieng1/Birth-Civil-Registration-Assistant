"""ASGI entrypoint: ``uvicorn crs_assistant.main:app``."""

from .api import create_app

app = create_app()
