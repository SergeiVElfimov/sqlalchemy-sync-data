import logging
import sqlite3
import threading
import typing
from datetime import datetime
from queue import Queue

import psycopg2
from psycopg2.extras import DictCursor

from .cursors import BaseCursor, HttpClickHouseCursor

logger = logging.getLogger(__name__)

BaseCursorType = typing.TypeVar("BaseCursorType", bound=BaseCursor)


class ConnectorException(Exception): ...


class BasicConnector(threading.Thread, typing.Generic[BaseCursorType]):
    """Connector class that should be used as connector attribute in Handlers.

    May be used as iterator object, but if you don't happy with it,
    you may use get_cursor method to get cursor for current connection
    to fetch data as you prefer. Also may be used as a separate thread.

    Params:
        connection_settings - connection settings.
        query - SQL query as string, e.g. SELECT id, code, name FROM products.
        output_queue - Required if running connector as separate process). Queue object to put fetching results in it.
        error_message - Error message.
    """

    _cursor: BaseCursorType
    _row = None

    def __init__(
        self,
        connection_settings,
        query,
        output_queue: Queue = Queue(),
        error_message: str = "ERROR",
        **kwargs,
    ):
        self._connection_settings = connection_settings
        self._query = query

        self._output_queue = output_queue
        self._error_message = error_message

        super().__init__(**kwargs)

    def make_connection_string(self):
        return self._connection_settings

    def get_cursor(self): ...

    def _get_row(self):
        return self._cursor.fetchone()

    def __iter__(self):
        self.__counter = 0
        logger.debug(
            f"{self.__class__.__name__} getting data with with the following settings:"
            f"""{self._connection_settings} and query: "{self._query}" """
        )
        self._cursor = self.get_cursor()
        start_date = datetime.now()
        self._cursor.execute(self._query)
        self._row = self._get_row()
        tdelta = datetime.now() - start_date
        logger.debug(f"Query {self._query} took {round(tdelta.seconds / 60, 2)} minutes to perform")
        return self

    def __next__(self):
        if self._row:
            curr_row = self._row
            self._row = self._get_row()
            self.__counter += 1
            return curr_row
        else:
            logger.debug(f"Finished fetching data from the database. {self.__counter} rows fetched")
            raise StopIteration

    def _check_process_ready(self):
        for r_attrib in (self._output_queue, self._error_message):
            if r_attrib is None:
                raise ValueError(f"{r_attrib} should not be None!")

    def run(self):
        self._check_process_ready()
        try:
            for row in self:
                self._output_queue.put(row)
        except Exception:
            self._output_queue.put(self._error_message)
            logger.exception("The error occurred while trying to fetch data from external database")


class SQLiteConnector(BasicConnector):
    def get_cursor(self):
        connect = sqlite3.connect(**self.make_connection_string())
        connect.row_factory = sqlite3.Row
        return connect.cursor()


class PostgresConnector(BasicConnector):
    def get_cursor(self):
        cursor = psycopg2.connect(**self.make_connection_string(), cursor_factory=DictCursor).cursor()
        return cursor


class HttpClickHouseConnector(BasicConnector):
    def __init__(self, connection_settings, query, output_queue=Queue(), **kwargs):
        raw_query, ordered_fields_with_type = query
        self._ordered_fields_with_type = ordered_fields_with_type
        super().__init__(connection_settings=connection_settings, query=raw_query, output_queue=output_queue, **kwargs)

    def make_connection_string(self):
        formatted_string = "{server}{database}{db_username}{db_password}".format(**self._connection_settings)
        return formatted_string

    def get_cursor(self):
        return HttpClickHouseCursor.connect(
            **self._connection_settings, query=self._query, ordered_fields_with_type=self._ordered_fields_with_type
        )
