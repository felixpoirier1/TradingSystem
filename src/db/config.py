import os
from dotenv import load_dotenv
load_dotenv(".config/.env")

# Database connection settings
DB_HOST = os.getenv("DB_HOST", "localhost")  # Default to localhost if not set
DB_PORT = int(os.getenv("DB_PORT", "5432"))  # Default to 5432 if not set
DB_NAME = os.getenv("DB_NAME", "trading_system_db")
DB_USER = os.getenv("DB_USER", "felix")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Luongo_12")

# SQLAlchemy connection string
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"