from sqlalchemy import text

from client import DatabaseClient
from models.book_msgs import PriceChange, BookSnapshot, TickSizeChange, Base
from config import DATABASE_URL




# Create a DatabaseClient instance
db_client = DatabaseClient(database_url=DATABASE_URL)

# Create the tables
db_client.create_tables(Base)
db_client.create_hypertable("price_changes", "time")

print("Database tables initialized.")