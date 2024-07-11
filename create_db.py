import os

from app import app, db
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, drop_database

def database_exists():
    return os.path.exists("instance/site.db")

def check_and_reset_database():
    # Check if the database exists
    if database_exists():
        print("Database exists.")
        # If it exists, drop/wipe the existing database
        os.remove("instance/site.db")
        print("Dropped the existing database.")

    # Recreate the database
    db.create_all()
    print("Created the new database.")

if __name__ == '__main__':
    with app.app_context():
        # Check and reset the database
        check_and_reset_database()
