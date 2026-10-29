from django.urls import path
from . import views

urlpatterns = [
    path('', views.inventory_view, name='inventory'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('transaction/add/', views.process_transaction, name='process_transaction'),
    path('transaction/cancel/<int:transaction_id>/', views.cancel_transaction, name='cancel_transaction'),
    path('history/', views.history_view, name='history'),
]