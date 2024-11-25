from app import app, socketio

# Die Migrationen werden jetzt in app.py ausgeführt
if __name__ == "__main__":
    socketio.run(app)
