#!/usr/bin/env bash

gunicorn startup:bulk \
         --bind=0.0.0.0:5000 \
         --timeout 60 \
         --graceful-timeout 60 \
         --keep-alive 120 \
         --workers 2
