from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def session_scope(*args, **kwargs):
    Session = sessionmaker(create_engine(*args, **kwargs))
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
