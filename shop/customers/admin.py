from django.contrib import admin
from .models import Customer, Product, StockAdjustment, Sale, SaleItem


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'created_at')
    search_fields = ('name', 'phone', 'email')
    list_filter = ('created_at',)
    ordering = ('-created_at',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'selling_price', 'cost_price', 'quantity', 'stock_status')
    search_fields = ('name', 'category')
    list_filter = ('category', 'created_at')
    ordering = ('name',)


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('product', 'adjustment_type', 'quantity', 'reason', 'created_by', 'created_at')
    list_filter = ('adjustment_type', 'created_at')
    search_fields = ('product__name', 'reason', 'notes')


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('line_total',)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'display_customer_name', 'total_amount', 'payment_method', 'date')
    search_fields = ('invoice_number', 'customer__name', 'customer_name', 'customer_phone')
    list_filter = ('payment_method', 'date')
    inlines = [SaleItemInline]
    readonly_fields = ('invoice_number', 'created_at')
