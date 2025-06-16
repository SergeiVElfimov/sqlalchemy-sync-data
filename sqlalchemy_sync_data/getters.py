import logging
import typing
from string import Formatter

from .connectors import BasicConnector, HttpClickHouseConnector, PostgresConnector

logger = logging.getLogger(__name__)
BasicConnectorType = typing.TypeVar("BasicConnectorType", bound=BasicConnector)


class BaseGetter(typing.Generic[BasicConnectorType]):
    """Base class for retrieving data from various sources."""

    connection_settings: dict = {}
    template_query: str = """"""
    connector: type[BasicConnectorType]
    fields_with_type: tuple[type] | tuple[()] = ()

    def __init__(self, **kwargs):
        # Check that the DB connection class is specified.
        if not self.connector:
            raise ValueError(f"connector not in class {self.__class__.__name__} attributes")
        # Check that the keys in the request template are present in the variables during initialization.
        fieldnames = [fname for _, fname, _, _ in Formatter().parse(self.template_query) if fname]
        for name in fieldnames:
            if name not in kwargs:
                raise ValueError(f"{name} not in class {self.__class__.__name__} attributes")
        self._kwargs = kwargs
        logger.debug(f"initialized instance class {self.__class__.__name__} with parameters {kwargs}")

    def make_query(self):
        return (
            (self.template_query.format(**self._kwargs), self.fields_with_type)
            if self.connector is HttpClickHouseConnector
            else self.template_query.format(**self._kwargs)
        )

    @property
    def query(self):
        return self.make_query()

    @property
    def _iter_response(self) -> typing.Iterable:
        """Getting an iterator from a connector to process data row by row."""
        logger.debug(
            f"{self.__class__.__name__} with kwargs {self._kwargs} sending to "
            f"{self.connector.__class__.__name__} query: {self.query}"
        )
        try:
            iterator = self.connector(connection_settings=self.connection_settings, query=self.query)
        except Exception as e:
            logger.exception(
                f"{self.__class__.__name__} sent to {self.connector.__class__.__name__} "
                f"query {self.query} and got the following exception: {e}"
            )
            raise e
        return iterator

    @property
    def _raw_response(self) -> tuple:
        """Converting an Iterator to a Tuple."""
        response = tuple(self._iter_response)
        logger.debug(
            f"{self.__class__.__name__} sent to {self.connector.__class__.__name__} query: "
            f"{self.query}. {self.connector.__class__.__name__} responded with:\n {response}"
        )
        return response

    def format_response(self, raw_response):
        return raw_response

    def get_response(self):
        return self.format_response(self._raw_response)

    def get_response_generator(self) -> typing.Generator:
        for row in self._iter_response:
            yield self.format_response((row,))[0]

    @property
    def response(self):
        return self.get_response()


class PostgresGetter(BaseGetter):
    """Base class for getting data from Postgres."""

    connector = PostgresConnector


class ClickHouseGetter(BaseGetter):
    """Base class for getting data from  ClickHouse."""

    connector = HttpClickHouseConnector
