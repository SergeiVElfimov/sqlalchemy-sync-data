import logging
import typing

from .handlers import BaseHandler

logger = logging.getLogger(__name__)

BaseHandlerType = typing.TypeVar("BaseHandlerType", bound=BaseHandler)


class BaseSyncronizator(typing.Generic[BaseHandlerType]):
    """Syncronizes data from external sources using handlers."""

    handler_classes: tuple[type[BaseHandlerType]] | tuple[()] = ()

    def run(self):
        for handler in self.handler_classes:
            logger.info(f"Starting to sync {handler}")
            try:
                hand_instance = handler()
                hand_instance.sync_catalogs()
                logger.info(f"Finished sync {handler}")
            except Exception as e:
                logger.exception(f"Handler {handler.__name__} failed with exception:")
                raise e
