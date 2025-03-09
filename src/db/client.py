from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from sqlalchemy import inspect
import logging

class DatabaseClient:
    def __init__(self, database_url):
        logging.debug(f"Launching instance of database at {database_url}")
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def create_tables(self, base):
        base.metadata.create_all(self.engine)

    def create_hypertable(self, table_name, time_column):
        with self.engine.connect() as connection:
            connection.execute(text(f"SELECT create_hypertable('{table_name}', '{time_column}');"))
            connection.commit()

    def check_table_exists(self, table_name):
        """Checks if a table exists in the database."""
        inspector = inspect(self.engine)
        return table_name in inspector.get_table_names()

    def get_table_columns(self, table_name):
        """Returns a list of column names for a given table."""
        inspector = inspect(self.engine)
        if self.check_table_exists(table_name):
            columns = inspector.get_columns(table_name)
            return [column['name'] for column in columns]
        else:
            return None

    def get_database_tables(self):
        """Returns a list of all table names in the database."""
        inspector = inspect(self.engine)
        return inspector.get_table_names()

    def check_database_connection(self):
        """Checks if the database connection is valid."""
        try:
            with self.engine.connect():
                return True
        except Exception:
            return False
