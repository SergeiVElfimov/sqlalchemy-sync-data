import pytz
from environs import Env

env = Env()
env.read_env(override=True)

SQLALCHEMY_SYNC_DATA_LOCAL_TIMEZONE = env.str("SQLALCHEMY_SYNC_DATA_LOCAL_TIMEZONE", "UTC")
TIME_ZONE = pytz.timezone(SQLALCHEMY_SYNC_DATA_LOCAL_TIMEZONE)
