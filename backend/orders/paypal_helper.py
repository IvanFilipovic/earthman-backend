import paypalrestsdk
from django.conf import settings

paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

def create_paypal_order(order_reference: str, total_amount: float, currency: str = 'EUR'):
    try:
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": f"{settings.FRONTEND_URL}/payment/paypal/success?order_ref={order_reference}",
                "cancel_url": f"{settings.FRONTEND_URL}/payment/paypal/cancel?order_ref={order_reference}"
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": f"Order {order_reference}",
                        "sku": order_reference,
                        "price": str(total_amount),
                        "currency": currency,
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(total_amount),
                    "currency": currency
                },
                "description": f"Payment for order {order_reference}"
            }]
        })

        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    return {
                        'success': True,
                        'payment_id': payment.id,
                        'approval_url': link.href
                    }
        else:
            return {
                'success': False,
                'error': payment.error
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def execute_paypal_payment(payment_id: str, payer_id: str):
    try:
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if payment.execute({"payer_id": payer_id}):
            return {
                'success': True,
                'payment_id': payment_id,
                'payer_id': payer_id,
                'state': payment.state
            }
        else:
            return {
                'success': False,
                'error': payment.error
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }