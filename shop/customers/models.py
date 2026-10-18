import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def total_orders(self):
        return self.sales.count()

    @property
    def total_spent(self):
        total = self.sales.aggregate(models.Sum('total_amount'))['total_amount__sum']
        return total or 0.00

    class Meta:
        ordering = ['-created_at']


class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Electronics', 'Electronics'),
        ('Clothing', 'Clothing'),
        ('Groceries', 'Groceries'),
        ('Stationery', 'Stationery'),
        ('Health & Beauty', 'Health & Beauty'),
        ('Home & Kitchen', 'Home & Kitchen'),
        ('General', 'General'),
    ]

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, default='General')
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def is_out_of_stock(self):
        return self.quantity <= 0

    @property
    def is_low_stock(self):
        return 0 < self.quantity <= self.low_stock_threshold

    @property
    def stock_status(self):
        if self.is_out_of_stock:
            return 'Out of Stock'
        elif self.is_low_stock:
            return 'Low Stock'
        return 'In Stock'

    @property
    def margin(self):
        return self.selling_price - self.cost_price

    @property
    def margin_percentage(self):
        if self.cost_price and self.cost_price > 0:
            return round(((self.selling_price - self.cost_price) / self.cost_price) * 100, 1)
        return 0.0

    class Meta:
        ordering = ['name']


class StockAdjustment(models.Model):
    ADJUSTMENT_TYPES = [
        ('ADD', 'Add Stock (+)'),
        ('REDUCE', 'Reduce Stock (-)'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='adjustments')
    adjustment_type = models.CharField(max_length=10, choices=ADJUSTMENT_TYPES)
    quantity = models.PositiveIntegerField()
    reason = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.get_adjustment_type_display()} ({self.quantity})"

    class Meta:
        ordering = ['-created_at']


class Sale(models.Model):
    PAYMENT_CHOICES = [
        ('Cash', 'Cash'),
        ('Card', 'Credit / Debit Card'),
        ('UPI', 'UPI / QR Code'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Other', 'Other'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    date = models.DateTimeField(default=timezone.now)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_CHOICES, default='Cash')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            date_prefix = timezone.now().strftime('%Y%m%d')
            unique_part = uuid.uuid4().hex[:6].upper()
            self.invoice_number = f"INV-{date_prefix}-{unique_part}"
        if self.customer and not self.customer_name:
            self.customer_name = self.customer.name
        if self.customer and not self.customer_phone:
            self.customer_phone = self.customer.phone
        super().save(*args, **kwargs)

    @property
    def display_customer_name(self):
        if self.customer:
            return self.customer.name
        return self.customer_name or 'Walk-in Customer'

    @property
    def total_items_count(self):
        return sum(item.quantity for item in self.items.all())

    def __str__(self):
        return f"{self.invoice_number} - {self.display_customer_name} ({self.total_amount})"

    class Meta:
        ordering = ['-date', '-created_at']


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} ({self.line_total})"
