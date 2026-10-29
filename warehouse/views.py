from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from decimal import Decimal
from .models import Item, Transaction, User
from django.core.exceptions import ValidationError


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                login(request, user)
                return redirect('inventory')
            else:
                messages.error(request, "Неверный пароль")
        except User.DoesNotExist:
            messages.error(request, "Пользователь не найден")
    return render(request, 'warehouse/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def inventory_view(request):
    query = request.GET.get('q', '')
    items = Item.objects.filter(is_archived=False)

    if query:
        items = items.filter(name__icontains=query)

    inventory_data = []
    # Считаем итоговые суммы по каждой валюте отдельно[cite: 2]
    totals = {'UZS': Decimal('0.00'), 'USD': Decimal('0.00'), 'CNY': Decimal('0.00')}

    for item in items:
        balance = item.get_balance()
        total_price = balance * item.price
        totals[item.currency] += total_price

        inventory_data.append({
            'item': item,
            'balance': balance,
            'total_price': total_price,
        })

    context = {
        'inventory_data': inventory_data,
        'totals': totals,
        'query': query,
    }
    return render(request, 'warehouse/inventory.html', context)


@login_required
def process_transaction(request):
    if request.user.role == 'manager':
        messages.error(request, "У менеджера нет прав на создание операций.")
        return redirect('inventory')

    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        transaction_type = request.POST.get('transaction_type')
        quantity_str = request.POST.get('quantity')
        location = request.POST.get('location', '')
        comment = request.POST.get('comment', '')

        try:
            quantity = Decimal(quantity_str)
            item = get_object_or_404(Item, id=item_id)

            tx = Transaction(
                transaction_type=transaction_type,
                item=item,
                quantity=quantity,
                location=location,
                comment=comment,
                user=request.user
            )
            tx.full_clean()
            tx.save()
            messages.success(request, "Операция успешно проведена!")
        except ValidationError as e:
            # Извлекаем только чистые тексты ошибок из списка e.messages
            messages.error(request, " ".join(e.messages))
        except Exception as e:
            messages.error(request, str(e))

    return redirect('inventory')


@login_required
def cancel_transaction(request, transaction_id):
    if request.user.role != 'admin':
        messages.error(request, "Только руководитель может отменять операции.")
        return redirect('history')

    original_tx = get_object_or_404(Transaction, id=transaction_id)

    cancel_tx = Transaction(
        transaction_type='cancel',
        item=original_tx.item,
        quantity=original_tx.quantity,
        user=request.user,
        canceled_transaction=original_tx,
        comment=f"Отмена операции №{original_tx.id}"
    )

    try:
        cancel_tx.full_clean()
        cancel_tx.save()
        messages.success(request, f"Операция №{original_tx.id} отменена.")
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    except Exception as e:
        messages.error(request, str(e))

    return redirect('history')
@login_required
def history_view(request):
    # Историю видят только Руководитель и Менеджер
    if request.user.role == 'storekeeper':
        messages.error(request, "У вас нет доступа к истории операций.")
        return redirect('inventory')

    transactions = Transaction.objects.select_related('item', 'user', 'canceled_transaction').order_by('-created_at')
    return render(request, 'warehouse/history.html', {'transactions': transactions})