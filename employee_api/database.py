import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


project_folder = Path(__file__).resolve().parent
load_dotenv(project_folder / ".env")


def get_connection():
    """Open and return a connection to the employee_management database."""
    required_settings = ["DB_HOST", "DB_USER", "DB_NAME"]
    missing_settings = [
        setting for setting in required_settings if not os.getenv(setting)
    ]

    if missing_settings:
        setting_names = ", ".join(missing_settings)
        raise ValueError(f"Missing database settings in .env: {setting_names}")

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME"),
    )


if __name__ == "__main__":
    connection = None

    try:
        connection = get_connection()
        print("Database connection successful.")
    except (ValueError, mysql.connector.Error) as error:
        print(f"Could not connect to the database: {error}")
    finally:
        if connection is not None and connection.is_connected():
            connection.close()
            print("Database connection closed.")
