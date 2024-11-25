# Team Workshop App

Eine interaktive Web-Anwendung für Team Workshops, die es ermöglicht, Fragen zu stellen und Antworten in Echtzeit zu sammeln.

## Features

- Host-Ansicht zum Erstellen von Fragen
- Teilnehmer können anonym über QR-Code beitreten
- Teilnehmer können eigene Fragen stellen
- Echtzeit-Updates für alle Teilnehmer
- Unterstützung für Text- und Multiple-Choice-Antworten
- Modernes UI mit DaisyUI
- Persistente Datenspeicherung mit PostgreSQL

## Lokale Entwicklung

1. Python-Abhängigkeiten installieren:
```bash
python -m venv venv
source venv/bin/activate  # Für Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Umgebungsvariablen konfigurieren:
- Kopiere `.env.example` zu `.env` und passe die Werte an
- Für lokale Entwicklung wird SQLite verwendet

3. Datenbank initialisieren:
```bash
flask db upgrade
```

4. Anwendung starten:
```bash
python app.py
```

## Deployment auf Railway

1. Erstelle ein neues Projekt auf Railway

2. Füge PostgreSQL als Service hinzu:
   - Railway Dashboard -> New -> Database -> Add PostgreSQL

3. Konfiguriere die Umgebungsvariablen:
   - `FLASK_ENV=production`
   - `SECRET_KEY=your-secure-secret-key`
   - `DATABASE_URL` (wird automatisch von Railway gesetzt)

4. Deploye den Code:
   - Verbinde dein GitHub-Repository
   - Railway wird automatisch den Code deployen

## Technologie-Stack

- Backend: Flask + Flask-SocketIO
- Frontend: HTML, JavaScript, Tailwind CSS + DaisyUI
- Datenbank: PostgreSQL (Production) / SQLite (Development)
- Echtzeit-Kommunikation: WebSocket
- QR-Code-Generierung: qrcode
