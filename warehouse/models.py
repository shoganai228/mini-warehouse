from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Sum
from decimal import Decimal


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Руководитель'),
        ('storekeeper', 'Кладовщик'),
        ('manager', 'Менеджер'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='manager')


class Item(models.Model):
    UNIT_CHOICES = (
        ('pcs', 'Штуки'),
        ('m', 'Метры'),
    )
    CURRENCY_CHOICES = (
        ('UZS', 'Сум'),
        ('USD', 'Доллар'),
        ('CNY', 'Юань'),
    )

    name = models.CharField(max_length=255, blank=False, null=False)
    unit = models.CharField(max_length=3, choices=UNIT_CHOICES)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def get_balance(self):
        # Находим ID всех оригинальных транзакций, которые были отменены
        canceled_ids = Transaction.objects.filter(
            transaction_type='cancel'
        ).values_list('canceled_transaction_id', flat=True)

        incomes = self.transaction_set.filter(
            transaction_type='in'
        ).exclude(id__in=canceled_ids).aggregate(total=Sum('quantity'))['total'] or Decimal('0.00')

        outcomes = self.transaction_set.filter(
            transaction_type='out'
        ).exclude(id__in=canceled_ids).aggregate(total=Sum('quantity'))['total'] or Decimal('0.00')

        return incomes - outcomes


class Transaction(models.Model):
    TYPE_CHOICES = (
        ('in', 'Приход'),
        ('out', 'Выдача'),
        ('cancel', 'Отмена'),
    )

    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    canceled_transaction = models.OneToOneField('self', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.item.name} ({self.quantity})"

    def clean(self):
        # Валидация для выдачи
        if self.transaction_type == 'out':
            if not self.location:
                raise ValidationError("Объект (адрес или имя клиента) обязателен при выдаче.")

            if self.item.unit == 'pcs' and self.quantity % 1 != 0:
                raise ValidationError("Количество в штуках может быть только целым числом.")

            balance = self.item.get_balance()
            if balance < self.quantity:
                raise ValidationError(f"На складе только {balance} {self.item.get_unit_display()}.")

        # Валидация для отмены
        elif self.transaction_type == 'cancel' and self.canceled_transaction:
            if Transaction.objects.filter(canceled_transaction=self.canceled_transaction).exists():
                raise ValidationError("Эта операция уже была отменена.")

            if self.canceled_transaction.transaction_type == 'in':
                balance = self.item.get_balance()
                if balance < self.canceled_transaction.quantity:
                    raise ValidationError("Отменить приход нельзя, товар из него уже выдан и остаток уйдёт в минус.")