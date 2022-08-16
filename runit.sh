#!/usr/bin/env bash

export FLASK_APP=startup

# added db initialization
flask db init
flask db migrate
flask db upgrade

gunicorn startup:bulk \
         --bind=0.0.0.0:5000 \
         --timeout 30 \
         --graceful-timeout 30 \
         --keep-alive 120 \
         --workers 2
