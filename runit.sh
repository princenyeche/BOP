#!/usr/bin/env bash

export FLASK_APP=startup
export FLASK_ENV=development

# added db initialization
flask db init
flask db migrate
flask db upgrade

gunicorn startup:bulk \
         --bind=0.0.0.0:5000 \
         --timeout 60 \
         --graceful-timeout 60 \
         --keep-alive 120 \
         --workers 2
