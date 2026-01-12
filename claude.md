# Django Webshop API - Code Review & Recommendations

**Review Date:** January 10, 2026
**Project:** Earthman Backend API
**Type:** Django REST API for E-commerce Platform

---

## Table of Contents
1. [Critical Security Issues](#critical-security-issues)
2. [High Priority Issues](#high-priority-issues)
3. [Medium Priority Issues](#medium-priority-issues)
4. [Code Quality Improvements](#code-quality-improvements)
5. [Performance Optimizations](#performance-optimizations)
6. [Missing Features & Recommendations](#missing-features--recommendations)
7. [Best Practices](#best-practices)
8. [Summary](#summary)

---

## Critical Security Issues

### 🔴 1. Hardcoded SECRET_KEY in Production
**File:** `backend/settings.py:26`
```python
SECRET_KEY = 'django-insecure-6+6v7wj$n$a=hu6hj(2a9&y2mj5fdust2ptxzokq(^kv07ap17'
```
**Severity:** CRITICAL
**Impact:** Complete compromise of session security, CSRF protection, and password reset tokens.

**Fix:**
```python
SECRET_KEY = config('SECRET_KEY')
```
Add to `.env` file with a strong random key.

---

### 🔴 2. DEBUG=True in Production
**File:** `backend/settings.py:29`
```python
DEBUG = True
```
**Severity:** CRITICAL
**Impact:** Exposes sensitive information including:
- Stack traces with code paths
- Database queries
- Environment variables
- Installed packages

**Fix:**
```python
DEBUG = config('DEBUG', default=False, cast=bool)
```

---

### 🔴 3. Exposed Email Credentials
**File:** `backend/settings.py:190-191`
```python
EMAIL_HOST_USER = "ivan.filipovic@exit-three.icu"
EMAIL_HOST_PASSWORD = ""  # Empty but exposed
```
**Severity:** CRITICAL
**Impact:** Email credentials visible in version control.

**Fix:** Move all email configuration to environment variables:
```python
EMAIL_HOST = config('EMAIL_HOST', default='smtp.office365.com')
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
```

---

### 🔴 4. CORS_ALLOW_ALL_ORIGINS = True
**File:** `backend/settings.py:50`
```python
CORS_ALLOW_ALL_ORIGINS = True
```
**Severity:** CRITICAL
**Impact:** Any website can make requests to your API, enabling CSRF attacks and data theft.

**Fix:**
```python
CORS_ALLOW_ALL_ORIGINS = False  # Remove this line entirely
# Keep only CORS_ALLOWED_ORIGINS list with specific domains
```

---

### 🔴 5. No Rate Limiting
**Severity:** CRITICAL
**Impact:** API vulnerable to:
- Brute force attacks on authentication
- DDoS attacks
- Cart spam
- Payment endpoint abuse

**Fix:** Implement `django-ratelimit` or DRF throttling:
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'payment': '5/minute',
    }
}
```

---

### 🔴 6. SQLite in Production
**File:** `backend/settings.py:136-141`
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```
**Severity:** CRITICAL
**Impact:**
- Not suitable for concurrent write operations
- No ACID guarantees under load
- Performance bottleneck
- Data loss risk

**Fix:** Use PostgreSQL:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}
```

---

### 🔴 7. No Input Validation for Quantities
**File:** `cart/views.py:37`
```python
if not quantity or int(quantity) < 1:
    return Response({"detail": "Quantity must be 1 or more."}, status=status.HTTP_400_BAD_REQUEST)
```
**Severity:** HIGH
**Impact:** No upper limit validation allows users to add millions of items, causing:
- Database overflow
- Price calculation errors
- Performance degradation

**Fix:**
```python
try:
    quantity = int(quantity)
    if quantity < 1 or quantity > 999:
        return Response(
            {"detail": "Quantity must be between 1 and 999."},
            status=status.HTTP_400_BAD_REQUEST
        )
except (ValueError, TypeError):
    return Response(
        {"detail": "Invalid quantity format."},
        status=status.HTTP_400_BAD_REQUEST
    )
```

---

### 🔴 8. No Payment Amount Verification
**File:** `orders/views.py:123-124`
```python
payment_intent = stripe.PaymentIntent.create(
    amount=int(order.total_price * 100),  # Trusts client-calculated price
```
**Severity:** CRITICAL
**Impact:** Price manipulation vulnerability. Malicious users could:
- Modify cart prices before payment
- Pay less than actual total
- Exploit race conditions

**Fix:** Always recalculate on server:
```python
# Recalculate total from database
calculated_total = Decimal('0.00')
for item in order.items.select_related('product_variant__product').all():
    product = item.product_variant.product
    unit_price = product.discount_price if product.discount else product.price
    calculated_total += unit_price * item.quantity
calculated_total += order.shipping_cost

# Verify against order total
if abs(calculated_total - order.total_price) > Decimal('0.01'):
    order.delete()
    return Response({"detail": "Price mismatch detected"}, status=400)

payment_intent = stripe.PaymentIntent.create(
    amount=int(calculated_total * 100),
    ...
)
```

---

## High Priority Issues

### 🟠 9. No Inventory Management
**Severity:** HIGH
**Impact:** Overselling products - accepting orders for out-of-stock items.

**Current State:** Models have `available` field but no quantity tracking.

**Fix:** Add inventory system:
```python
# In common/models.py - ProductVariant
class ProductVariant(models.Model):
    # ... existing fields ...
    stock_quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)

    @property
    def available(self):
        return self.stock_quantity > 0

    def reserve_stock(self, quantity):
        """Atomically reserve stock for an order"""
        from django.db.models import F
        updated = ProductVariant.objects.filter(
            id=self.id,
            stock_quantity__gte=quantity
        ).update(stock_quantity=F('stock_quantity') - quantity)
        return updated > 0
```

Then in order creation:
```python
# orders/views.py - CreateOrderView
for item in cart.items.all():
    if not item.product_variant.reserve_stock(item.quantity):
        # Rollback any reserved stock
        return Response(
            {"detail": f"{item.product_variant} is out of stock"},
            status=400
        )
    OrderItem.objects.create(...)
```

---

### 🟠 10. No Transaction Atomicity in Order Creation
**File:** `orders/views.py:84-110`
**Severity:** HIGH
**Impact:** Partial order creation if database errors occur mid-process.

**Fix:** Wrap in atomic transaction:
```python
from django.db import transaction

class CreateOrderView(APIView):
    @transaction.atomic
    def post(self, request):
        # ... existing code ...
        # All database operations now rollback on error
```

---

### 🟠 11. Missing Email Validation
**Severity:** HIGH
**Impact:** Invalid emails cause order creation failures and prevent customer notifications.

**Fix:** Add email validator:
```python
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

# In CreateOrderView
try:
    validate_email(customer_data["email"])
except ValidationError:
    return Response(
        {"detail": "Invalid email address."},
        status=status.HTTP_400_BAD_REQUEST
    )
```

---

### 🟠 12. No Webhook Signature Verification Logging
**File:** `orders/views.py:265-276`
**Severity:** HIGH
**Impact:** Failed webhook attempts go unnoticed, potentially missing payment confirmations.

**Fix:** Add comprehensive logging:
```python
import logging
logger = logging.getLogger(__name__)

def post(self, request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(...)
    except ValueError as e:
        logger.error(f"Stripe webhook invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Stripe webhook signature verification failed: {e}")
        return HttpResponse(status=400)
```

---

### 🟠 13. Duplicate Email Configuration
**File:** `backend/settings.py:186-194` and `216-223`
**Severity:** MEDIUM
**Impact:** Configuration confusion, settings override each other.

**Fix:** Remove duplicate EMAIL_BACKEND declaration and consolidate:
```python
# Email Configuration (Outlook/Office 365)
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.office365.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='EARTHMAN <noreply@earth-man.eu>')
STAFF_ORDER_EMAIL = config('STAFF_ORDER_EMAIL', default='orders@earth-man.eu')
EMAIL_TIMEOUT = 10
```

---

### 🟠 14. No Phone Number Validation
**File:** `orders/views.py:64`
**Severity:** MEDIUM
**Impact:** Invalid phone numbers stored, preventing customer contact.

**Fix:** Use `phonenumbers` library:
```python
import phonenumbers
from phonenumbers import NumberParseException

try:
    parsed = phonenumbers.parse(customer_data["phone_number"], customer_data.get("country"))
    if not phonenumbers.is_valid_number(parsed):
        return Response({"detail": "Invalid phone number"}, status=400)
    customer_data["phone_number"] = phonenumbers.format_number(
        parsed, phonenumbers.PhoneNumberFormat.E164
    )
except NumberParseException:
    return Response({"detail": "Invalid phone number format"}, status=400)
```

---

## Medium Priority Issues

### 🟡 15. No Abandoned Cart Recovery
**Severity:** MEDIUM
**Impact:** Lost revenue from abandoned carts (typically 60-80% of carts).

**Recommendation:** Implement scheduled task to identify and email users about abandoned carts:
```python
# cart/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

@shared_task
def send_abandoned_cart_emails():
    """Send emails for carts abandoned 24 hours ago"""
    cutoff = timezone.now() - timedelta(hours=24)
    carts = Cart.objects.filter(
        updated_at__lte=cutoff,
        updated_at__gte=cutoff - timedelta(hours=1),
        items__isnull=False
    ).distinct()

    for cart in carts:
        # Get email from session or guest
        # Send reminder email
        pass
```

Add to Celery beat schedule:
```python
# settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'send-abandoned-cart-emails': {
        'task': 'cart.tasks.send_abandoned_cart_emails',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
    },
}
```

---

### 🟡 16. No Old Cart Cleanup (As Requested)
**Severity:** MEDIUM
**Impact:** Database bloat from old cart data.

**Recommendation:** Implement cron job to delete carts older than 8 days:
```python
# cart/management/commands/cleanup_old_carts.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from cart.models import Cart

class Command(BaseCommand):
    help = 'Delete carts older than 8 days'

    def handle(self, *args, **options):
        cutoff_date = timezone.now() - timedelta(days=8)
        old_carts = Cart.objects.filter(updated_at__lt=cutoff_date)
        count = old_carts.count()
        old_carts.delete()
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {count} old carts')
        )
```

**Using Celery Beat (Recommended):**
```python
# cart/tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Cart
import logging

logger = logging.getLogger(__name__)

@shared_task
def cleanup_old_carts():
    """Delete carts older than 8 days"""
    cutoff_date = timezone.now() - timedelta(days=8)
    old_carts = Cart.objects.filter(updated_at__lt=cutoff_date)
    count = old_carts.count()

    if count > 0:
        old_carts.delete()
        logger.info(f'Deleted {count} carts older than 8 days')
    else:
        logger.info('No old carts to delete')

    return f'Deleted {count} carts'
```

Add to settings.py:
```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'cleanup-old-carts': {
        'task': 'cart.tasks.cleanup_old_carts',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
```

Run with: `celery -A backend beat --loglevel=info`

---

### 🟡 17. No Order Status Tracking for Customers
**Severity:** MEDIUM
**Impact:** Customers cannot track their order status without contacting support.

**Fix:** Add order tracking endpoint:
```python
# orders/views.py
class OrderTrackingView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, order_reference):
        email = request.query_params.get('email')
        if not email:
            return Response({"detail": "Email required"}, status=400)

        try:
            order = Order.objects.get(order_reference=order_reference, email=email)
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
```

---

### 🟡 18. Missing Logging Configuration
**Severity:** MEDIUM
**Impact:** Difficult to debug production issues.

**Fix:** Add comprehensive logging:
```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/django.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/errors.log',
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'orders': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'cart': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

Create logs directory:
```bash
mkdir -p backend/logs
```

---

### 🟡 19. PayPal Cart Cleanup Logic Issue
**File:** `orders/views.py:367-376`
```python
if order.guest:
    carts = Cart.objects.filter(items__isnull=False).distinct()
    for cart in carts:
        cart.items.all().delete()
        cart.delete()
        break  # Only deletes first cart!
```
**Severity:** MEDIUM
**Impact:** Deletes random user's cart instead of the order's cart.

**Fix:** Store cart session in order metadata:
```python
# In CreateOrderView, for PayPal
order.metadata = {'cart_session_id': session_id}  # Add JSONField to Order model

# In ExecutePayPalPaymentView
session_id = order.metadata.get('cart_session_id')
if session_id:
    try:
        cart = Cart.objects.get(session_id=session_id)
        cart.delete()
    except Cart.DoesNotExist:
        pass
```

---

### 🟡 20. No HTTPS Enforcement
**Severity:** MEDIUM
**Impact:** Data transmitted in plain text (passwords, payment info, etc.)

**Fix:**
```python
# settings.py
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
```

---

## Code Quality Improvements

### 🔵 21. Inconsistent Error Handling
**Severity:** LOW
**Impact:** Inconsistent API responses.

**Example:** Some views return `{"detail": "..."}`, others return different formats.

**Fix:** Create custom exception handler:
```python
# common/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        custom_response = {
            'success': False,
            'error': response.data.get('detail', str(exc)),
            'status_code': response.status_code
        }
        response.data = custom_response

    return response

# settings.py
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'common.exceptions.custom_exception_handler',
    # ... other settings
}
```

---

### 🔵 22. Missing Model `__str__` Methods Quality
**File:** `common/models.py:110`
```python
def __str__(self):
    return f"{self.product.name} - {self.color.color} - {self.size.name}"
    # AttributeError if color.color doesn't exist
```
**Severity:** LOW
**Impact:** Admin interface crashes.

**Fix:**
```python
def __str__(self):
    try:
        color_name = self.color.color.name if hasattr(self.color, 'color') else str(self.color)
        return f"{self.product.name} - {color_name} - {self.size.name}"
    except AttributeError:
        return f"ProductVariant {self.id}"
```

---

### 🔵 23. Unused Celery Tasks
**File:** `orders/tasks.py`
**Severity:** LOW
**Impact:** Dead code, refers to non-existent utilities.

**Issue:** Tasks reference `build_order_confirmation_email` and `build_order_shipped_email` from `orders.utils`, but these functions don't exist. The actual email logic is in `orders/emails.py`.

**Fix:** Remove unused tasks or update them to use the correct functions:
```python
# Either remove tasks.py entirely or update:
@shared_task
def send_order_confirmation_email_task(order_id):
    from .emails import send_order_emails
    try:
        order = Order.objects.get(id=order_id)
        send_order_emails(order)
    except Order.DoesNotExist:
        pass
```

---

### 🔵 24. Missing Type Hints
**Severity:** LOW
**Impact:** Reduced code maintainability.

**Recommendation:** Add type hints:
```python
from typing import Optional, Tuple, Dict, Any
from decimal import Decimal

def send_order_emails(order: Order) -> Tuple[bool, bool]:
    """Send order confirmation emails to both customer and staff"""
    ...

def calculate_total(self) -> Decimal:
    """Calculate order total including shipping"""
    ...
```

---

### 🔵 25. Comments in Multiple Languages
**File:** `common/models.py`
```python
# Model za kolekcije (Serbian)
# Model za boje (Serbian)
```
**Severity:** LOW
**Impact:** Code readability for international teams.

**Fix:** Use English for all code comments:
```python
# Collection model
# Color model
```

---

### 🔵 26. Verbose Name Plural Mismatch
**File:** `common/models.py:42-47`
```python
class Categories(models.Model):  # Plural name
    name = models.CharField(max_length=50)

    class Meta:
        verbose_name = "category"  # Singular
        verbose_name_plural = "categories"
```
**Severity:** LOW
**Impact:** Confusing naming.

**Fix:** Rename model to `Category`:
```python
class Category(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = "categories"
```

---

## Performance Optimizations

### ⚡ 27. N+1 Query Problems
**Severity:** MEDIUM
**Impact:** Performance degradation with many orders/products.

**Example:** Order serializer doesn't prefetch related data.

**Fix:**
```python
# orders/views.py - UserOrdersView
def get(self, request):
    orders = Order.objects.prefetch_related(
        'items__product_variant__product',
        'items__product_variant__color__color',
        'items__product_variant__size'
    ).select_related('user', 'guest').filter(
        user=request.user
    ).order_by('-created_at')

    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
```

---

### ⚡ 28. Missing Database Indexes
**Severity:** MEDIUM
**Impact:** Slow queries on large datasets.

**Fix:** Add indexes:
```python
class Order(models.Model):
    # ... existing fields ...

    class Meta:
        indexes = [
            models.Index(fields=['order_reference']),
            models.Index(fields=['email']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['-created_at']),  # For ordering
        ]

class Cart(models.Model):
    session_id = models.CharField(max_length=255, unique=True, db_index=True)
    # ... existing fields ...

    class Meta:
        indexes = [
            models.Index(fields=['updated_at']),
            models.Index(fields=['created_at']),
        ]
```

---

### ⚡ 29. No Caching Strategy
**Severity:** MEDIUM
**Impact:** Repeated database queries for static data (colors, sizes, categories).

**Fix:** Implement Redis caching:
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# common/views.py
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

@method_decorator(cache_page(60 * 60), name='dispatch')  # Cache 1 hour
class ColorListView(generics.ListAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
```

---

### ⚡ 30. Missing Select/Prefetch Related
**File:** `orders/views.py:199`
```python
order = Order.objects.get(order_reference=order_reference)
```
**Severity:** LOW
**Impact:** Additional queries when accessing related items.

**Fix:**
```python
order = Order.objects.prefetch_related('items__product_variant__product').get(
    order_reference=order_reference
)
```

---

## Missing Features & Recommendations

### 💡 31. No Order Cancellation
**Recommendation:** Allow users to cancel orders within a time window:
```python
class CancelOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_reference):
        try:
            order = Order.objects.get(
                order_reference=order_reference,
                user=request.user
            )

            # Only allow cancellation within 1 hour of creation
            if timezone.now() - order.created_at > timedelta(hours=1):
                return Response(
                    {"detail": "Order cannot be cancelled after 1 hour"},
                    status=400
                )

            if order.payment_status == 'paid':
                # Initiate refund via Stripe/PayPal
                pass

            order.status = 'cancelled'
            order.save()

            # Release inventory
            for item in order.items.all():
                item.product_variant.release_stock(item.quantity)

            return Response({"detail": "Order cancelled successfully"})

        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
```

---

### 💡 32. No Refund Handling
**Recommendation:** Implement refund workflow:
```python
class RefundOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_reference):
        order = Order.objects.get(
            order_reference=order_reference,
            user=request.user,
            payment_status='paid'
        )

        if order.payment_method == 'card':
            # Stripe refund
            refund = stripe.Refund.create(
                payment_intent=order.stripe_payment_intent_id
            )
            order.payment_status = 'refunded'
            order.save()

        # Send refund confirmation email
        return Response({"detail": "Refund processed"})
```

---

### 💡 33. No Admin Notifications
**Recommendation:** Send real-time notifications to staff:
- Low stock alerts
- Failed payment attempts
- High-value orders (> €500)
- Unusual activity (bulk orders, etc.)

```python
# common/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=ProductVariant)
def check_low_stock(sender, instance, **kwargs):
    if instance.stock_quantity <= instance.low_stock_threshold:
        # Send email to staff
        send_mail(
            f'Low Stock Alert: {instance.product.name}',
            f'Only {instance.stock_quantity} units remaining',
            settings.DEFAULT_FROM_EMAIL,
            [settings.STAFF_ORDER_EMAIL]
        )
```

---

### 💡 34. No Product Reviews/Ratings
**Recommendation:** Add review system:
```python
class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    verified_purchase = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')
```

---

### 💡 35. No Wishlist Feature
**Recommendation:** Add wishlist for authenticated users:
```python
class Wishlist(models.Model):
    user = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)

class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('wishlist', 'product_variant')
```

---

### 💡 36. No Discount Codes/Coupons
**Recommendation:** Implement coupon system:
```python
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(
        max_length=20,
        choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')]
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    def is_valid(self):
        now = timezone.now()
        if not self.active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False
        return True
```

---

### 💡 37. No Email Verification
**Recommendation:** Verify customer emails:
```python
class Customer(AbstractBaseUser, PermissionsMixin):
    # ... existing fields ...
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True)

    def send_verification_email(self):
        token = uuid.uuid4().hex
        self.verification_token = token
        self.save()

        verification_url = f"{settings.FRONTEND_URL}/verify-email/{token}/"
        send_mail(
            'Verify Your Email',
            f'Click here to verify: {verification_url}',
            settings.DEFAULT_FROM_EMAIL,
            [self.email]
        )
```

---

### 💡 38. No Order Invoice Generation
**Recommendation:** Generate PDF invoices:
```python
from reportlab.pdfgen import canvas
from django.http import HttpResponse

class OrderInvoiceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_reference):
        order = Order.objects.get(
            order_reference=order_reference,
            user=request.user
        )

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order_reference}.pdf"'

        # Generate PDF using reportlab
        p = canvas.Canvas(response)
        p.drawString(100, 750, f"Invoice - {order.order_reference}")
        # ... add order details ...
        p.showPage()
        p.save()

        return response
```

---

### 💡 39. No Analytics/Reporting
**Recommendation:** Add basic analytics:
```python
class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        from django.db.models import Sum, Count, Avg

        stats = {
            'total_revenue': Order.objects.filter(
                payment_status='paid'
            ).aggregate(Sum('total_price'))['total_price__sum'],

            'orders_today': Order.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),

            'average_order_value': Order.objects.filter(
                payment_status='paid'
            ).aggregate(Avg('total_price'))['total_price__avg'],

            'top_products': Product.objects.annotate(
                order_count=Count('variants__orderitem')
            ).order_by('-order_count')[:10],
        }

        return Response(stats)
```

---

### 💡 40. No Shipping Cost Calculation
**File:** `orders/models.py:70`
```python
shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=10.00)
```
**Recommendation:** Dynamic shipping based on:
- Location/country
- Order weight/size
- Delivery speed

```python
def calculate_shipping_cost(country, total_weight, delivery_speed='standard'):
    SHIPPING_RATES = {
        'domestic': {'standard': 5.00, 'express': 15.00},
        'EU': {'standard': 10.00, 'express': 25.00},
        'international': {'standard': 20.00, 'express': 40.00},
    }

    zone = 'domestic' if country == 'HR' else 'EU' if country in EU_COUNTRIES else 'international'
    base_rate = SHIPPING_RATES[zone][delivery_speed]

    # Add weight-based fee
    if total_weight > 5:  # kg
        base_rate += (total_weight - 5) * 2

    return Decimal(str(base_rate))
```

---

### 💡 41. No Guest Order Tracking
**Issue:** Guests can't track orders without logging in.

**Recommendation:** Add magic link or order lookup:
```python
class GuestOrderTrackingView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        order_reference = request.data.get('order_reference')

        try:
            order = Order.objects.get(
                order_reference=order_reference,
                email=email
            )

            # Send magic link
            token = uuid.uuid4().hex
            cache.set(f'order_token_{token}', order.id, timeout=3600)  # 1 hour

            tracking_url = f"{settings.FRONTEND_URL}/track/{token}/"
            send_mail(
                'Track Your Order',
                f'Click here to track your order: {tracking_url}',
                settings.DEFAULT_FROM_EMAIL,
                [email]
            )

            return Response({"detail": "Tracking link sent to your email"})
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)
```

---

## Best Practices

### ✅ 42. Add API Versioning
**Recommendation:**
```python
# urls.py
urlpatterns = [
    path('api/v1/', include('orders.urls')),
    path('api/v1/', include('cart.urls')),
    # ... etc
]
```

---

### ✅ 43. Add GDPR Compliance Features
**Recommendation:**
- Data export endpoint
- Account deletion
- Cookie consent tracking
- Data retention policies

```python
class ExportUserDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            'personal_info': {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'orders': OrderSerializer(user.orders.all(), many=True).data,
            # ... other data
        }
        return Response(data)

class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        # Anonymize instead of delete to preserve order history
        user.email = f"deleted_{user.id}@deleted.com"
        user.first_name = "Deleted"
        user.last_name = "User"
        user.is_active = False
        user.save()
        return Response({"detail": "Account deleted"})
```

---

### ✅ 44. Add Comprehensive Testing
**Recommendation:** Add test coverage for critical paths:
```python
# orders/tests.py
from django.test import TestCase
from rest_framework.test import APIClient
from decimal import Decimal

class OrderCreationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # ... setup test data

    def test_create_order_with_valid_data(self):
        response = self.client.post('/api/orders/create/', {
            'email': 'test@example.com',
            # ... other fields
        })
        self.assertEqual(response.status_code, 201)

    def test_create_order_prevents_price_manipulation(self):
        # Test that server recalculates prices
        pass

    def test_stripe_webhook_updates_order_status(self):
        pass
```

Run tests with coverage:
```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

---

### ✅ 45. Add Health Check Endpoint
**Recommendation:**
```python
class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.db import connection

        health = {
            'status': 'healthy',
            'database': False,
            'redis': False,
        }

        # Check database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health['database'] = True
        except Exception:
            health['status'] = 'unhealthy'

        # Check Redis
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 1)
            health['redis'] = cache.get('health_check') == 'ok'
        except Exception:
            health['status'] = 'unhealthy'

        status_code = 200 if health['status'] == 'healthy' else 503
        return Response(health, status=status_code)
```

---

### ✅ 46. Add Requirements Management
**File:** `requirements.txt`
**Issue:** No version pinning, missing packages.

**Fix:**
```txt
# Core
Django==5.0.7
djangorestframework==3.14.0
django-cors-headers==4.0.0
django-filter==23.1
python-decouple==3.8

# Authentication
djangorestframework-simplejwt==5.3.1
PyJWT==2.8.0

# Database
psycopg2-binary==2.9.9  # For PostgreSQL

# Payment
stripe==7.0.0
paypalrestsdk==1.13.1

# Task Queue
celery==5.5.3
redis==5.0.1
django-redis==5.4.0

# Admin
django-import-export==3.3.4
django-daisy==1.1.1

# API Documentation
drf-yasg==1.21.6

# Production Server
gunicorn==23.0.0

# Email
django-ses==3.5.0  # For Amazon SES (optional)

# Utilities
Pillow==10.1.0
phonenumbers==8.13.26
reportlab==4.0.7  # For PDF generation

# Security
django-ratelimit==4.1.0

# Development
django-debug-toolbar==4.2.0
ipython==8.18.0

# Testing
pytest==7.4.3
pytest-django==4.7.0
factory-boy==3.3.0
coverage==7.3.2
```

Create separate files:
- `requirements/base.txt`
- `requirements/development.txt`
- `requirements/production.txt`

---

### ✅ 47. Add Environment Template
**Recommendation:** Create `.env.example`:
```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=earthman_db
DB_USER=earthman_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@earth-man.eu
EMAIL_HOST_PASSWORD=your_email_password
DEFAULT_FROM_EMAIL=EARTHMAN <noreply@earth-man.eu>
STAFF_ORDER_EMAIL=orders@earth-man.eu

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# PayPal
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret

# Frontend
FRONTEND_URL=http://localhost:3000

# Redis
REDIS_URL=redis://localhost:6379/0
```

---

### ✅ 48. Add Docker Support
**Recommendation:** Create `Dockerfile` and `docker-compose.yml`:

```dockerfile
# Dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: earthman_db
      POSTGRES_USER: earthman_user
      POSTGRES_PASSWORD: your_password

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  web:
    build: .
    command: gunicorn backend.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    env_file:
      - .env

  celery:
    build: .
    command: celery -A backend worker -l info
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    env_file:
      - .env

  celery-beat:
    build: .
    command: celery -A backend beat -l info
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    env_file:
      - .env

volumes:
  postgres_data:
```

---

### ✅ 49. Add CI/CD Pipeline
**Recommendation:** Create `.github/workflows/django.yml`:
```yaml
name: Django CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt

    - name: Run migrations
      run: |
        python manage.py migrate

    - name: Run tests
      run: |
        python manage.py test

    - name: Run linting
      run: |
        pip install flake8
        flake8 . --exclude=migrations,venv
```

---

### ✅ 50. Add API Documentation Improvements
**File:** `backend/urls.py:11-22`
**Issue:** Generic placeholder text.

**Fix:**
```python
schema_view = get_schema_view(
    openapi.Info(
        title="Earthman E-commerce API",
        default_version='v1',
        description="""
        RESTful API for Earthman webshop platform.

        Features:
        - Product catalog with variants (colors, sizes)
        - Session-based shopping cart
        - Multiple payment methods (Stripe, PayPal, Cash on Delivery, Bank Transfer)
        - Order management and tracking
        - JWT authentication

        For support, contact: orders@earth-man.eu
        """,
        terms_of_service="https://earth-man.eu/terms/",
        contact=openapi.Contact(email="orders@earth-man.eu"),
        license=openapi.License(name="Proprietary"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)
```

---

## Summary

### Critical Issues (Must Fix Before Production)
1. ✅ Hardcoded SECRET_KEY
2. ✅ DEBUG=True
3. ✅ Exposed email credentials
4. ✅ CORS_ALLOW_ALL_ORIGINS=True
5. ✅ No rate limiting
6. ✅ SQLite database
7. ✅ No input validation for quantities
8. ✅ No payment amount verification

### High Priority (Fix Soon)
9. ✅ No inventory management
10. ✅ No transaction atomicity
11. ✅ Missing email validation
12. ✅ No webhook logging
13. ✅ Duplicate email configuration
14. ✅ No phone number validation

### Medium Priority (Plan to Implement)
15. ✅ Abandoned cart recovery
16. ✅ **Old cart cleanup (8-day cron job)** ← Your specific request
17. ✅ Order status tracking
18. ✅ Logging configuration
19. ✅ PayPal cart cleanup bug
20. ✅ HTTPS enforcement

### Recommended Features
- Product reviews and ratings
- Wishlist functionality
- Discount codes/coupons
- Email verification
- Invoice generation
- Analytics dashboard
- Guest order tracking
- GDPR compliance tools

### Infrastructure Improvements
- Docker containerization
- CI/CD pipeline
- Comprehensive testing
- Health check endpoints
- API versioning
- Monitoring and alerts

---

## Implementation Priority

### Week 1 (Critical Security)
- [ ] Move SECRET_KEY to .env
- [ ] Set DEBUG=False for production
- [ ] Fix CORS settings
- [ ] Add rate limiting
- [ ] Migrate to PostgreSQL
- [ ] Add input validation

### Week 2 (Payment Security)
- [ ] Add server-side price verification
- [ ] Implement transaction atomicity
- [ ] Add comprehensive logging
- [ ] Fix webhook error handling

### Week 3 (Core Features)
- [ ] Implement inventory management
- [ ] Add database indexes
- [ ] Setup caching with Redis
- [ ] Implement cart cleanup cron job (8 days)

### Week 4 (Additional Features)
- [ ] Add abandoned cart emails
- [ ] Implement order tracking
- [ ] Add GDPR compliance features
- [ ] Setup monitoring

---

## API Usage Examples

### Customer Information with Orders

**Endpoint:** `GET /api/customers/me/`

**Description:** Retrieve authenticated customer's information including all their orders.

**Authentication:** Required (Bearer Token)

**Request Example:**
```bash
curl -X GET "http://localhost:8000/api/customers/me/" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  -H "Content-Type: application/json"
```

**Response Example:**
```json
{
  "id": 1,
  "email": "customer@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "newsletter": true,
  "is_active": true,
  "date_joined": "2026-01-10T10:30:00Z",
  "orders": [
    {
      "id": 5,
      "order_reference": "ORD-A1B2C3D4E5",
      "email": "customer@example.com",
      "country": "Croatia",
      "address": "Main Street 123",
      "city": "Zagreb",
      "postal_code": "10000",
      "delivery_address": "",
      "delivery_city": "",
      "delivery_postal_code": "",
      "phone_number": "+385912345678",
      "payment_method": "card",
      "payment_status": "paid",
      "transaction_id": "pi_3Ab12CdEfGhIjKlM",
      "total_price": "125.00",
      "shipping_cost": "10.00",
      "status": "shipped",
      "tracking_number": "TRK123456789",
      "created_at": "2026-01-12T14:25:00Z",
      "items": [
        {
          "id": 8,
          "product_variant": {
            "id": 15,
            "product": {
              "id": 3,
              "name": "Cotton T-Shirt",
              "price": "29.99",
              "discount": true,
              "discount_price": "24.99"
            },
            "color": {
              "id": 2,
              "color": {
                "name": "Blue"
              }
            },
            "size": {
              "id": 3,
              "name": "M"
            },
            "sku": "TSH-BLU-M",
            "available": true
          },
          "quantity": 2
        },
        {
          "id": 9,
          "product_variant": {
            "id": 22,
            "product": {
              "id": 7,
              "name": "Denim Jeans",
              "price": "79.99",
              "discount": false,
              "discount_price": null
            },
            "color": {
              "id": 5,
              "color": {
                "name": "Dark Blue"
              }
            },
            "size": {
              "id": 4,
              "name": "L"
            },
            "sku": "JNS-DBL-L",
            "available": true
          },
          "quantity": 1
        }
      ]
    },
    {
      "id": 3,
      "order_reference": "ORD-F6G7H8I9J0",
      "email": "customer@example.com",
      "country": "Croatia",
      "address": "Main Street 123",
      "city": "Zagreb",
      "postal_code": "10000",
      "phone_number": "+385912345678",
      "payment_method": "paypal",
      "payment_status": "paid",
      "transaction_id": "PAYID-M1234567890",
      "total_price": "55.98",
      "shipping_cost": "10.00",
      "status": "delivered",
      "tracking_number": "TRK987654321",
      "created_at": "2026-01-05T09:15:00Z",
      "items": [
        {
          "id": 5,
          "product_variant": {
            "id": 8,
            "product": {
              "id": 2,
              "name": "Summer Dress",
              "price": "45.98",
              "discount": false,
              "discount_price": null
            },
            "color": {
              "id": 1,
              "color": {
                "name": "Red"
              }
            },
            "size": {
              "id": 2,
              "name": "S"
            },
            "sku": "DRS-RED-S",
            "available": true
          },
          "quantity": 1
        }
      ]
    }
  ]
}
```

**Notes:**
- Orders are returned in reverse chronological order (newest first)
- All order items include complete product variant details
- Response uses efficient database queries with `prefetch_related`
- This endpoint replaces the deprecated `orders/my/` endpoint

**Update Customer Information:**
```bash
curl -X PATCH "http://localhost:8000/api/customers/me/" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Smith",
    "newsletter": false
  }'
```

---

## Maintenance Tasks

### Daily
- Monitor error logs
- Check payment webhook failures
- Review order confirmations

### Weekly
- Review abandoned cart statistics
- Check inventory levels
- Analyze sales data

### Monthly
- Database backup verification
- Security updates
- Performance optimization review

---

**End of Report**

For questions or clarifications, please review specific line numbers mentioned in each issue.
