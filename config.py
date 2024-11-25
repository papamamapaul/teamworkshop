import os
from dotenv import load_dotenv

load_dotenv()

def get_database_url():
    """Get database URL and fix it if necessary."""
    url = os.getenv('DATABASE_URL')
    if url is None:
        return 'sqlite:///workshop.db'
    
    # Fix Railway's postgres:// URLs to work with SQLAlchemy
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///workshop.db'

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = get_database_url()

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
