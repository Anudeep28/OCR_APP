# ocr_app/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, OCRDocument

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_app_user')
    list_filter = ('is_staff', 'is_superuser', 'is_app_user')
    fieldsets = UserAdmin.fieldsets + (
        ('App Access', {'fields': ('is_app_user',)}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(OCRDocument)