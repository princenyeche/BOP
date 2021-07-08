web: flask db upgrade; gunicorn startup:bulk
worker: rq worker -u $REDIS_URL bulkops-jobs
