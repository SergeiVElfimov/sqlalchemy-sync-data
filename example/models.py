from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

CommonBase = declarative_base()


class User(CommonBase):
    __tablename__ = "old_users"

    id = Column(Integer, autoincrement=True, unique=True, primary_key=True, nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
