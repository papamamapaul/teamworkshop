#!/bin/bash
pip install -r requirements.txt
export FLASK_APP=app.py
python -m flask db upgrade
