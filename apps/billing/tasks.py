from celery import shared_task

from . import services


@shared_task
def generate_monthly_invoices():
    created = services.generate_monthly_invoices()
    return {"created": len(created)}


@shared_task
def mark_overdue_invoices():
    updated = services.mark_overdue_invoices()
    return {"updated": updated}


@shared_task
def purge_old_canceled_invoices():
    deleted = services.purge_old_canceled_invoices()
    return {"deleted": deleted}
