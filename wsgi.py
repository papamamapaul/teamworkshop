from app import create_app, socketio

app = create_app()

# Die Migrationen werden jetzt in app.py ausgeführt
if __name__ == "__main__":
    socketio.run(app)
