"""
[WHY] Flask configuration for CircusCircus. Loads DB URI from .env for Docker/PostgreSQL support.
[SECURITY] Never hardcode secrets in source files; use .env for credentials.
[IMPORT] dotenv for .env loading, os for env vars.
"""
from os import environ, path
from dotenv import load_dotenv

basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))

class Config:
    """[CLASS] Flask config object. Loads DB URI from env, falls back to SQLite for dev."""
    # [FIELD] General Config
    SECRET_KEY = 'kristofer'  # [SECURITY] Replace in production
    FLASK_APP = 'forum.app'

    # [FIELD] Database
    SQLALCHEMY_DATABASE_URI = environ.get('DATABASE_URL', 'sqlite:///circuscircus.db')
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
