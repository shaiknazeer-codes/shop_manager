from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import Customer, Product, StockAdjustment, Sale


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'email', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer Name', 'required': True}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Full Address', 'rows': 3}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            raise ValidationError("Phone number is required.")
        return phone


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'selling_price', 'cost_price', 'quantity', 'low_stock_threshold', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name', 'required': True}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category (e.g. Groceries, Electronics)', 'list': 'category-list'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': '0'}),
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '10', 'min': '0'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Product Description', 'rows': 3}),
        }

    def clean_selling_price(self):
        price = self.cleaned_data.get('selling_price')
        if price is not None and price < 0:
            raise ValidationError("Selling price cannot be negative.")
        return price

    def clean_cost_price(self):
        price = self.cleaned_data.get('cost_price')
        if price is not None and price < 0:
            raise ValidationError("Cost price cannot be negative.")
        return price

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is not None and qty < 0:
            raise ValidationError("Quantity cannot be negative.")
        return qty


class StockAdjustmentForm(forms.ModelForm):
    REASON_CHOICES = [
        ('Received Shipment', 'Received Shipment / New Stock'),
        ('Inventory Recount', 'Inventory Recount / Audit Correction'),
        ('Customer Return', 'Customer Return'),
        ('Damaged / Expired', 'Damaged / Expired Goods'),
        ('Loss / Theft', 'Loss / Theft'),
        ('Correction', 'Correction of Entry Error'),
        ('Other', 'Other'),
    ]

    reason_choice = forms.ChoiceField(
        choices=REASON_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = StockAdjustment
        fields = ['adjustment_type', 'quantity', 'notes']
        widgets = {
            'adjustment_type': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'Units to adjust'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Additional details or memo...', 'rows': 2}),
        }

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if not qty or qty <= 0:
            raise ValidationError("Adjustment quantity must be at least 1.")
        return qty


class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email
