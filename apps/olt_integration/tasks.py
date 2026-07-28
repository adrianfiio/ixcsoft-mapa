from celery import shared_task

@shared_task
def health_task():
    return {"app": "olt_integration", "status": "ok"}
