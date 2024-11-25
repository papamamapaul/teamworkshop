from app import create_app
from flask_migrate import upgrade
import os

app = create_app()

# Führe Migrationen beim Start aus
with app.app_context():
    upgrade()
