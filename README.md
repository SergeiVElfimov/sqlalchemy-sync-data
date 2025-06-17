# SQLAlchemy sync data

Synchronization of data from different sources into one database using SQLAlchemy.

## Examples

```python
# models.py
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String

CommonBase = declarative_base()


class User(CommonBase):
    __tablename__ = "old_users"

    id = Column(Integer, autoincrement=True, unique=True, primary_key=True, nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)


# getters.py

from sqlalchemy_sync_data.getters import SQLiteGetter


class UserGetter(SQLiteGetter):
    template_query = """select id, first_name, last_name, email from users"""
    connection_settings = {"database": "sqlalchemy_sync_data.sqlite"}

# handlers.py

from sqlalchemy_sync_data.handlers import BaseHandler
from .getters import UserGetter
from .models import User

class UserHandler(BaseHandler):
    model = User
    db_fields_to_model_mapping = {
        "id": "id",
        "first_name": "first_name",
        "last_name": "last_name",
        "email": "username",
    }
    field_name_as_external_id = 'id'
    getter_class = UserGetter

# synchronizators.py

from sqlalchemy_sync_data.synchronizator import BaseSyncronizator
from .handlers import UserHandler

class UserSyncronizator(BaseSyncronizator):
    handler_classes = (UserHandler,)

# Run sync data
from .synchronizators import UserSyncronizator

syncronizator = UserSyncronizator()
syncronizator.run()
```

## Environment variables

SQLALCHEMY_SYNC_DATA_LOCAL_TIMEZONE - setting time zone (default value "UTC").

## Required

- python >=3.11, <4.0
- fastapi >=0.100.0, <1.0
- SQLAlchemy >=1.4.36, <2.1.0
- requests >=2.32.3
- psycopg2 >=2.9.5
- pytz >=2020.1
- environs >=9.3.1

## Installation
```pip install sqlalchemy-sync-data```

## Contribution

You can run tests with `pytest`.

```
pip install poetry
poetry install
pytest
```
