from celery import Celery

# Broker = queue; Backend = where task states/results are stored
celery = Celery(
    "vidavox_doc_ai",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

celery.conf.update(
    task_track_started=True,
    task_time_limit=60*60,      # hard kill if it goes too long
    task_soft_time_limit=60*45,  # soft timeout (cleanup window)
)
