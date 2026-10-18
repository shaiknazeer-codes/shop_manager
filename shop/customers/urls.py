from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alt'),

    # Authentication
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Customer Management
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/add/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_update, name='customer_update'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),

    # Product Management
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),

    # Inventory Management
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/adjust/', views.stock_adjust, name='stock_adjust'),
    path('inventory/adjust/<int:pk>/', views.stock_adjust, name='product_stock_adjust'),

    # Sales and Billing
    path('sales/', views.sale_list, name='sale_list'),
    path('sales/new/', views.sale_create, name='sale_create'),
    path('sales/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('sales/<int:pk>/invoice/', views.invoice_print, name='invoice_print'),

    # Reports
    path('reports/', views.reports_view, name='reports'),
]
