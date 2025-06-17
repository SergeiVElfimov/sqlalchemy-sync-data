from abc import ABC, abstractmethod

import requests


class BaseCursor(ABC):
    connection_timeout: int

    @abstractmethod
    def connect(self, *args, **kwargs): ...

    @abstractmethod
    def fetchone(self): ...

    @abstractmethod
    def execute(self, *args, **kwargs): ...


class HttpCursor(BaseCursor):
    connection_timeout = 20

    def __init__(self, json_data: list, ordered_fields: tuple | list | set):
        self.__counter = 0
        self.__json_data = json_data
        self.__ordered_fields = ordered_fields

    @classmethod
    def connect(cls, url: str, ordered_fields: list):
        response = requests.get(url, timeout=cls.connection_timeout)
        json_data = response.json()
        instance = cls(json_data=json_data, ordered_fields=ordered_fields)
        return instance

    def execute(self, *args, **kwargs): ...

    def fetchone(self):
        try:
            raw_row = self.__json_data[self.__counter]
            row = ()
            for field_name in self.__ordered_fields:
                row += (raw_row[field_name],)  # type: ignore
            self.__counter += 1
        except IndexError:
            row = None
        return row


class HttpClickHouseCursor(BaseCursor):
    connection_timeout = 20

    def __init__(self, text_data: list[list[str]], ordered_fields_with_type: tuple[tuple]):
        self.__counter = 0
        self.__text_data = text_data
        self.__ordered_fields_with_type = ordered_fields_with_type

    @classmethod
    def connect(cls, host: str, user: str, password: str, query: str, ordered_fields_with_type: tuple[tuple]):
        response = requests.get(
            host,
            timeout=cls.connection_timeout,
            params={
                "query": query,
            },
            headers={
                "X-ClickHouse-User": user,
                "X-ClickHouse-Key": password,
            },
        )
        text_data = [row.split("\t") for row in response.text.split("\n")[:-1]]
        return cls(text_data=text_data, ordered_fields_with_type=ordered_fields_with_type)

    def execute(self, *args, **kwargs): ...

    def fetchone(self):
        try:
            raw_row = self.__text_data[self.__counter]
            row = {}
            for index, field_with_type in enumerate(self.__ordered_fields_with_type):
                field_name, _type = field_with_type
                row[field_name] = _type(raw_row[index])
            self.__counter += 1
        except IndexError:
            row = None
        return row
