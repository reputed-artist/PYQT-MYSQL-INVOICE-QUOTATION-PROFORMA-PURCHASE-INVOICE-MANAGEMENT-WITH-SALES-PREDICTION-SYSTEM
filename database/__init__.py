"""database package - re-export the data layer for `from database import ...`."""
from database.db_manager import *  # noqa: F401,F403
from database.db_manager import DB, DOC_REGISTRY, get_connection

