from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.network_map.models import FiberCable
from apps.optical.services.fiber_generator import FiberGenerator


@receiver(post_save, sender=FiberCable)
def generate_fibers(sender, instance, created, **kwargs):
    if not created:
        return

    if not instance.cable_model_id:
        return

    FiberGenerator(instance).generate()
