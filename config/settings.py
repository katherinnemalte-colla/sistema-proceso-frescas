from dotenv import load_dotenv
import os

load_dotenv()

DB_SERVER = os.getenv("DB_SERVER")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_DATABASE_1 = os.getenv("DB_DATABASE_1")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")