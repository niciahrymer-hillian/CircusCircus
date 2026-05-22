"""
Flask configuration variables.
"""

from os import environ, path
from dotenv import load_dotenv

basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))

class Config:
    """Set Flask configuration from .env file."""
    # General Config
    SECRET_KEY = environ.get('SECRET_KEY')
    FLASK_APP = 'forum.app'

    # Database
    # Use DATABASE_URL from .env, fallback to SQLite for local dev
    # For Docker/PostgreSQL: postgresql://ccuser:<password>@db/circuscircus
    # Note: host must be 'db' (Docker service name), not 'localhost'
    SQLALCHEMY_DATABASE_URI = environ.get('DATABASE_URL', 'sqlite:///circuscircus.db')
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False