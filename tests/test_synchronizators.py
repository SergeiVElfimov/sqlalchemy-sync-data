from sqlalchemy import func

from example.models import User
from example.synchronizators import UserSyncronizator


def test_syncronizator(users, db_session):
    syncronizator = UserSyncronizator()
    syncronizator.run()

    assert db_session.query(func.count(User.id)).scalar() == len(users)

    users_with_id = {instance.id: instance for instance in users}
    old_users_with_id = {instance.id: instance for instance in db_session.query(User).all()}

    for _id, user in users_with_id.items():
        old_user = old_users_with_id[_id]

        for field_name in ("id", "first_name", "last_name"):
            assert getattr(user, field_name) == getattr(old_user, field_name)

        assert user.email == old_user.username
