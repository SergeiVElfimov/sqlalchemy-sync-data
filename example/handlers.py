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
    field_name_as_external_id = "id"
    getter_class = UserGetter
    connection_settings = {"url": "sqlite:///sqlalchemy_sync_data.sqlite"}
