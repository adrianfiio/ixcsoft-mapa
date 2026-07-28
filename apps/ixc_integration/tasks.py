from celery import shared_task

@shared_task
def health_task():
    return {"app": "ixc_integration", "status": "ok"}
