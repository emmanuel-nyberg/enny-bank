#!/bin/bash
nginx && gunicorn --workers 4 --bind 0.0.0.0:5000 wsgi:app && celery -A tasks.celery worker
