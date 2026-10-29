from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Item, Transaction


class CustomUserAdmin(UserAdmin):
    # Выводим роль в список пользователей
    list_display = ('username', 'role', 'is_staff')

    # Добавляем роль в форму редактирования пользователя
    fieldsets = UserAdmin.fieldsets + (
        ('Права и роли', {'fields': ('role',)}),
    )

    # Добавляем роль в форму создания пользователя
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Права и роли', {'fields': ('role',)}),
    )


admin.site.register(User, CustomUserAdmin)
admin.site.register(Item)
admin.site.register(Transaction)