from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Customer, Guest

@admin.register(Customer)
class CustomerAdmin(BaseUserAdmin):
    model = Customer
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active', 'newsletter')
    list_filter = ('is_staff', 'is_active', 'newsletter')
    search_fields = ('email',)
    ordering = ('email',)
    readonly_fields = ('date_joined',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'newsletter')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ('email', 'newsletter', 'created_at')
    search_fields = ('email',)
    ordering = ('-created_at',)