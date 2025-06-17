from sqlalchemy_sync_data.getters import SQLiteGetter


class UserGetter(SQLiteGetter):
    template_query = """select id, first_name, last_name, email from users"""
    connection_settings = {"database": "sqlalchemy_sync_data.sqlite"}
