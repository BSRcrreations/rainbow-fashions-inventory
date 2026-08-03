from sqlalchemy.orm import configure_mappers

import app.models  # noqa: F401


def test_all_model_relationships_configure() -> None:
    configure_mappers()
