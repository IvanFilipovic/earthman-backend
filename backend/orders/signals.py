from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order
from .tasks import send_order_confirmation_email_task, send_order_shipped_email_task

@receiver(post_save, sender=Order)
def order_post_save(sender, instance, created, **kwargs):
    if created:
        send_order_confirmation_email_task.delay(instance.id)
    elif hasattr(instance, '_previous_status') and instance._previous_status != instance.status:
        if instance.status == 'shipped':
            send_order_shipped_email_task.delay(instance.id)
