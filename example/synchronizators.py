from sqlalchemy_sync_data.synchronizator import BaseSyncronizator

from .handlers import UserHandler


class UserSyncronizator(BaseSyncronizator):
    handler_classes = (UserHandler,)
