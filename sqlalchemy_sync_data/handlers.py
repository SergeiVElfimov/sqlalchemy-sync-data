import logging
import typing
from contextlib import suppress
from datetime import datetime
from queue import Queue

from sqlalchemy.orm import DeclarativeBase

from .connection import session_scope
from .getters import BaseGetter
from .settings import TIME_ZONE
from .string_key_dict import StringKeyedDict
from .utils import batch

logger = logging.getLogger(__name__)


ModelType = typing.TypeVar("ModelType", bound=DeclarativeBase)


class BaseHandler(typing.Generic[ModelType]):
    """Base class for processing data from external databases and storing them in the project database.

    Attributes:
        none_synonyms: A set of values that should be set to Null when parsing a string.
        model: Model of sqlalchemy.
        db_fields_to_model_mapping: Mapping getter fields to model of sqlalchemy field names.
        field_name_as_external_id: Field to use as primary key.
        tuple_fields_name_as_external_id: Fields to use as primary key.
        max_batch_size: Batch size when processing objects from a getter.
        getter_class: Getter for loading data from external systems.
    """

    __timezone = TIME_ZONE
    none_synonyms = frozenset(
        {
            None,
        }
    )

    model: type[ModelType]
    db_fields_to_model_mapping: dict[str, str] = {}
    field_name_as_external_id: str = ""
    max_batch_size: int = 60000
    getter_class = BaseGetter
    tuple_fields_name_as_external_id: tuple[str] | tuple[()] = ()
    connection_settings: dict[str, typing.Any] = {}

    def __init__(self):
        self._session = next(session_scope(**self.connection_settings))
        self._table_columns = tuple(self.db_fields_to_model_mapping.keys())
        self._attributes = tuple(self.db_fields_to_model_mapping.values())
        self._parsed_data: Queue = Queue()
        self._parsed_to_create: Queue = Queue()
        self._parsed_to_update: Queue = Queue()
        self._entries_received = 0
        if self.field_name_as_external_id and self.tuple_fields_name_as_external_id:
            raise AttributeError(
                f"{self.__class__.__name__} cannot fill attributes "
                f""""field_name_as_external_id" and "tuple_fields_name_as_external_id" """
            )

        if self.field_name_as_external_id:
            self._pks: dict[str, typing.Any] = self._make_pk_dict()
        elif self.tuple_fields_name_as_external_id:
            self._pks = self._make_pks_dict()

    def get_queryset(self):
        return self._session.query(self.model).all()

    def _make_pk_dict(self) -> dict:
        initial_dict = {getattr(instance, self.field_name_as_external_id): instance for instance in self.get_queryset()}
        return StringKeyedDict(initial_dict)

    def _make_pks_dict(self) -> dict:
        initial_dict = {
            "_".join(
                [str(getattr(instance, field_name)) for field_name in self.tuple_fields_name_as_external_id]
            ): instance
            for instance in self.get_queryset()
        }
        return StringKeyedDict(initial_dict)

    def _distribute_queues(self):
        while not self._parsed_data.empty():
            parsed_dict = self._parsed_data.get()
            if (
                self.field_name_as_external_id
                and parsed_dict[self.field_name_as_external_id] in self._pks
                or (
                    self.tuple_fields_name_as_external_id
                    and "_".join([str(parsed_dict[field_name]) for field_name in self.tuple_fields_name_as_external_id])
                    in self._pks
                )
            ):
                self._parsed_to_update.put(parsed_dict)
            else:
                self._parsed_to_create.put(parsed_dict)

    def convert_value(self, row_value: typing.Any) -> typing.Any:
        """Convert the raw value.

        :param row_value: Raw value.
        :return: Value.
        """
        if isinstance(row_value, str):
            with suppress(TypeError, ValueError):
                row_value = float(row_value) if "." in row_value else int(row_value)
        elif isinstance(row_value, datetime):
            row_value = row_value.replace(tzinfo=self.__timezone)
        return row_value

    def _parse_row(self, raw_response: dict) -> dict:
        """Transform the response from the getter, with a dictionary with keys of the column names in the model.

        :param raw_response: dict
        :return: dict with keys named after field names and values as converted data
        """
        parsed_row = {}
        for attribute, table_column in self.db_fields_to_model_mapping.items():
            row_value = raw_response[attribute]
            row_value = self.convert_value(row_value) if row_value not in self.none_synonyms else None
            parsed_row[table_column] = row_value
        return parsed_row

    def parse_row(self, raw_response: dict) -> None:
        self._parsed_data.put(self._parse_row(raw_response))

    def _get_getter(self):
        return self.getter_class()

    def _get_data_from_db(self):
        """Convert row from getter into dict with keys equal to model field names.

        :param row: list or tuple
        :return: dict with keys named after field names and values as converted data
        """
        logger.info(f"Getting data with {self.__class__.__name__}")

        getter = self._get_getter()

        n = 0
        for fetched_row in getter.response:
            n += 1
            self._entries_received += 1
            self.parse_row(fetched_row)
            if n == self.max_batch_size:
                self._save_data()
                n = 0
        logger.info(f"{self._entries_received} rows parsed from external db")

    def _bulk_load(self):
        """Big INSERT.

        :return: None
        """
        instances = []
        while not self._parsed_to_create.empty():
            params = self._parsed_to_create.get()
            instance = self.model(**params)
            instances.append(instance)
        if instances:
            for chunk in batch(instances, batch_size=self.max_batch_size // 10):
                self._session.add_all(chunk)
                self._session.commit()

    def _bulk_update(self):
        """Big UPDATE.

        :return: None
        """
        instances_with_params = []
        while not self._parsed_to_update.empty():
            params = self._parsed_to_update.get()
            if self.field_name_as_external_id:
                pk_value: str = params.pop(self.field_name_as_external_id)
            elif self.tuple_fields_name_as_external_id:
                list_pk_value = []
                for field_name in self.tuple_fields_name_as_external_id:
                    list_pk_value.append(str(params.pop(field_name)))
                pk_value = "_".join(list_pk_value)
            instance = self._pks[pk_value]
            instances_with_params.append((instance, params))

        if instances_with_params:
            for chunk in batch(instances_with_params, batch_size=self.max_batch_size // 10):
                for instance, params in chunk:
                    for field_name, value in params.items():
                        setattr(instance, field_name, value)
                self._session.commit()

    def _save_data(self):
        """If external_id_field_name attribute declared, updates or creates existing models.

        if not, only makes INSERT into DB.
        :return: None
        """
        self._distribute_queues()
        self._bulk_update()
        self._bulk_load()

    def sync_catalogs(self):
        try:
            self._get_data_from_db()
            self._save_data()
            logger.info(f"Storing data for {self.__class__.__name__} finished successfully")
        except Exception as e:
            logger.exception(f"Getting data with {self.__class__.__name__} failed with error")
            raise e
        finally:
            self._session.close()
