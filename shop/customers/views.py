from decimal import Decimal
from datetime import timedelta
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, models
from django.db.models import Sum, Count, F, Q, DecimalField, ExpressionWrapper
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from django.core.paginator import Paginator

from .models import Customer, Product, StockAdjustment, Sale, SaleItem
from .forms import CustomerForm, ProductForm, StockAdjustmentForm, UserRegistrationForm


# ==========================================
# AUTHENTICATION VIEWS
# ==========================================

def register_view(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Account created successfully for {user.username}! Please log in.")
            return redirect('login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserRegistrationForm()

    return render(request, 'registration/register.html', {'form': form})


def logout_view(request):
    """Custom logout view supporting GET and POST."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


# ==========================================
# DASHBOARD
# ==========================================

@login_required
def dashboard(request):
    """Main shop dashboard showing key business indicators and metrics."""
    today = timezone.localdate()

    # Core statistics
    total_products = Product.objects.count()
    total_customers = Customer.objects.count()
    total_stock_qty = Product.objects.aggregate(total=Sum('quantity'))['total'] or 0

    # Today's sales & revenue
    today_sales = Sale.objects.filter(date__date=today)
    today_sales_count = today_sales.count()
    today_revenue = today_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # This month's revenue
    first_of_month = today.replace(day=1)
    month_sales = Sale.objects.filter(date__date__gte=first_of_month)
    month_revenue = month_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # Inventory alerts
    low_stock_products = Product.objects.filter(
        quantity__lte=F('low_stock_threshold')
    ).order_by('quantity')[:8]
    low_stock_count = Product.objects.filter(quantity__lte=F('low_stock_threshold')).count()

    # Recent sales
    recent_sales = Sale.objects.select_related('customer').order_by('-date', '-created_at')[:8]

    # Inventory total retail value
    total_inventory_value = sum(p.quantity * p.selling_price for p in Product.objects.all() if p.quantity > 0)

    context = {
        'total_products': total_products,
        'total_customers': total_customers,
        'total_stock_qty': total_stock_qty,
        'today_sales_count': today_sales_count,
        'today_revenue': today_revenue,
        'month_revenue': month_revenue,
        'low_stock_products': low_stock_products,
        'low_stock_count': low_stock_count,
        'recent_sales': recent_sales,
        'total_inventory_value': total_inventory_value,
        'today_date': today,
    }
    return render(request, 'dashboard.html', context)


# ==========================================
# CUSTOMER MANAGEMENT (CRUD)
# ==========================================

@login_required
def customer_list(request):
    """View and search customers."""
    q = request.GET.get('q', '').strip()
    customers = Customer.objects.all()

    if q:
        customers = customers.filter(
            Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q)
        )

    # Annotate total spent and order count
    customers = customers.annotate(
        sales_count=Count('sales'),
        spent_sum=Sum('sales__total_amount')
    ).order_by('-created_at')

    paginator = Paginator(customers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'customers/customer_list.html', {
        'customers': page_obj,
        'q': q,
        'total_count': customers.count(),
    })


@login_required
def customer_create(request):
    """Create a new customer."""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f"Customer '{customer.name}' added successfully.")
            return redirect('customer_list')
        else:
            messages.error(request, "Please check the form for errors.")
    else:
        form = CustomerForm()

    return render(request, 'customers/customer_form.html', {
        'form': form,
        'title': 'Add New Customer',
        'is_edit': False,
    })


@login_required
def customer_update(request, pk):
    """Edit existing customer."""
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f"Customer '{customer.name}' updated successfully.")
            return redirect('customer_list')
        else:
            messages.error(request, "Please check the form for errors.")
    else:
        form = CustomerForm(instance=customer)

    return render(request, 'customers/customer_form.html', {
        'form': form,
        'customer': customer,
        'title': f"Edit Customer - {customer.name}",
        'is_edit': True,
    })


@login_required
def customer_detail(request, pk):
    """Customer profile and purchase history."""
    customer = get_object_or_404(Customer, pk=pk)
    sales = customer.sales.order_by('-date')

    total_spent = sales.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')

    return render(request, 'customers/customer_detail.html', {
        'customer': customer,
        'sales': sales,
        'total_spent': total_spent,
    })


@login_required
def customer_delete(request, pk):
    """Delete a customer with confirmation."""
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        name = customer.name
        # Keep sales records intact by detaching customer before deletion
        customer.sales.update(customer=None, customer_name=name)
        customer.delete()
        messages.success(request, f"Customer '{name}' deleted successfully.")
        return redirect('customer_list')

    return render(request, 'customers/customer_confirm_delete.html', {'customer': customer})


# ==========================================
# PRODUCT MANAGEMENT (CRUD)
# ==========================================

@login_required
def product_list(request):
    """View, search, and filter products."""
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    status = request.GET.get('status', '').strip()

    products = Product.objects.all()

    if q:
        products = products.filter(Q(name__icontains=q) | Q(description__icontains=q))

    if category:
        products = products.filter(category=category)

    if status == 'low':
        products = products.filter(quantity__lte=F('low_stock_threshold'), quantity__gt=0)
    elif status == 'out':
        products = products.filter(quantity__lte=0)
    elif status == 'in':
        products = products.filter(quantity__gt=F('low_stock_threshold'))

    categories = Product.objects.values_list('category', flat=True).distinct()

    paginator = Paginator(products, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'products/product_list.html', {
        'products': page_obj,
        'q': q,
        'selected_category': category,
        'selected_status': status,
        'categories': sorted(list(set(c for c in categories if c))),
        'total_count': products.count(),
    })


@login_required
def product_create(request):
    """Add a new product."""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' created successfully.")
            return redirect('product_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm()

    existing_categories = Product.objects.values_list('category', flat=True).distinct()

    return render(request, 'products/product_form.html', {
        'form': form,
        'title': 'Add New Product',
        'is_edit': False,
        'categories': sorted(list(set(c for c in existing_categories if c))),
    })


@login_required
def product_update(request, pk):
    """Edit product details."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' updated successfully.")
            return redirect('product_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm(instance=product)

    existing_categories = Product.objects.values_list('category', flat=True).distinct()

    return render(request, 'products/product_form.html', {
        'form': form,
        'product': product,
        'title': f"Edit Product - {product.name}",
        'is_edit': True,
        'categories': sorted(list(set(c for c in existing_categories if c))),
    })


@login_required
def product_delete(request, pk):
    """Delete a product with confirmation."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        name = product.name
        try:
            product.delete()
            messages.success(request, f"Product '{name}' deleted successfully.")
            return redirect('product_list')
        except models.ProtectedError:
            messages.error(
                request,
                f"Cannot delete '{name}' because it has been sold in existing invoices. "
                "Consider setting its quantity to 0 instead."
            )
            return redirect('product_list')

    return render(request, 'products/product_confirm_delete.html', {'product': product})


# ==========================================
# INVENTORY MANAGEMENT
# ==========================================

@login_required
def inventory_list(request):
    """Inventory overview and stock tracking."""
    filter_type = request.GET.get('filter', 'all')
    q = request.GET.get('q', '').strip()

    products = Product.objects.all().order_by('quantity', 'name')

    if q:
        products = products.filter(name__icontains=q)

    total_units = Product.objects.aggregate(total=Sum('quantity'))['total'] or 0
    low_stock_count = Product.objects.filter(quantity__lte=F('low_stock_threshold'), quantity__gt=0).count()
    out_of_stock_count = Product.objects.filter(quantity__lte=0).count()
    in_stock_count = Product.objects.filter(quantity__gt=F('low_stock_threshold')).count()

    if filter_type == 'low':
        products = products.filter(quantity__lte=F('low_stock_threshold'), quantity__gt=0)
    elif filter_type == 'out':
        products = products.filter(quantity__lte=0)
    elif filter_type == 'alerts':
        products = products.filter(quantity__lte=F('low_stock_threshold'))

    # Recent adjustments
    recent_adjustments = StockAdjustment.objects.select_related('product', 'created_by').order_by('-created_at')[:10]

    paginator = Paginator(products, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'inventory/inventory_list.html', {
        'products': page_obj,
        'filter_type': filter_type,
        'q': q,
        'total_units': total_units,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'in_stock_count': in_stock_count,
        'recent_adjustments': recent_adjustments,
    })


@login_required
def stock_adjust(request, pk=None):
    """Adjust product stock with audit logging."""
    product = None
    if pk:
        product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        product_id = request.POST.get('product_id') or (product.id if product else None)
        selected_product = get_object_or_404(Product, pk=product_id)
        form = StockAdjustmentForm(request.POST)

        if form.is_valid():
            adj_type = form.cleaned_data['adjustment_type']
            qty = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason_choice']
            notes = form.cleaned_data['notes']

            with transaction.atomic():
                # Lock product record for update
                locked_product = Product.objects.select_for_update().get(pk=selected_product.pk)

                if adj_type == 'REDUCE':
                    if locked_product.quantity < qty:
                        messages.error(
                            request,
                            f"Cannot reduce by {qty} units. Current stock for '{locked_product.name}' is only {locked_product.quantity}."
                        )
                        return redirect('inventory_list')
                    locked_product.quantity -= qty
                else:  # ADD
                    locked_product.quantity += qty

                locked_product.save()

                StockAdjustment.objects.create(
                    product=locked_product,
                    adjustment_type=adj_type,
                    quantity=qty,
                    reason=reason,
                    notes=notes,
                    created_by=request.user
                )

            action_text = "added to" if adj_type == 'ADD' else "deducted from"
            messages.success(
                request,
                f"Successfully {action_text} stock for '{locked_product.name}'. New stock: {locked_product.quantity}."
            )
            return redirect('inventory_list')
        else:
            messages.error(request, "Please check form entries.")
    else:
        form = StockAdjustmentForm()

    all_products = Product.objects.all().order_by('name')

    return render(request, 'inventory/stock_adjust.html', {
        'form': form,
        'product': product,
        'all_products': all_products,
    })


# ==========================================
# SALES AND BILLING
# ==========================================

@login_required
def sale_create(request):
    """
    POS / Billing view.
    Allows multi-item sale creation, stock validation, and atomic inventory reduction.
    """
    if request.method == 'POST':
        customer_id = request.POST.get('customer')
        customer_name = request.POST.get('customer_name', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        payment_method = request.POST.get('payment_method', 'Cash')
        notes = request.POST.get('notes', '').strip()

        # Discount & Tax
        try:
            discount = Decimal(request.POST.get('discount', '0') or '0')
            if discount < 0:
                discount = Decimal('0.00')
        except Exception:
            discount = Decimal('0.00')

        try:
            tax_rate = Decimal(request.POST.get('tax_rate', '0') or '0')
            if tax_rate < 0:
                tax_rate = Decimal('0.00')
        except Exception:
            tax_rate = Decimal('0.00')

        # Line items from POST lists
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        unit_prices = request.POST.getlist('unit_price[]')

        if not product_ids or len(product_ids) == 0:
            messages.error(request, "A sale must include at least one product.")
            return redirect('sale_create')

        # Gather and validate items
        items_to_process = []
        for pid, qty_str, price_str in zip(product_ids, quantities, unit_prices):
            if not pid or not qty_str:
                continue
            try:
                pid = int(pid)
                qty = int(qty_str)
                if qty <= 0:
                    messages.error(request, "Quantity must be greater than zero.")
                    return redirect('sale_create')
                price = Decimal(price_str)
                if price < 0:
                    price = Decimal('0.00')
                items_to_process.append({'product_id': pid, 'quantity': qty, 'unit_price': price})
            except (ValueError, TypeError):
                messages.error(request, "Invalid product quantity or price entered.")
                return redirect('sale_create')

        if not items_to_process:
            messages.error(request, "Please add at least one valid product.")
            return redirect('sale_create')

        # Process transaction atomically
        try:
            with transaction.atomic():
                # Customer attachment
                customer = None
                if customer_id:
                    customer = Customer.objects.filter(pk=customer_id).first()
                    if customer and not customer_name:
                        customer_name = customer.name
                    if customer and not customer_phone:
                        customer_phone = customer.phone

                if not customer_name:
                    customer_name = 'Walk-in Customer'

                # Verify stock for ALL products first with lock
                p_ids = [item['product_id'] for item in items_to_process]
                # Lock rows to prevent race condition
                locked_products = {
                    p.id: p for p in Product.objects.select_for_update().filter(id__in=p_ids)
                }

                # Check quantities
                subtotal = Decimal('0.00')
                for item in items_to_process:
                    prod = locked_products.get(item['product_id'])
                    if not prod:
                        raise ValueError(f"Product with ID #{item['product_id']} not found.")
                    if prod.quantity < item['quantity']:
                        raise ValueError(
                            f"Insufficient stock for '{prod.name}'. "
                            f"Available: {prod.quantity}, Requested: {item['quantity']}."
                        )
                    # Snapshot current cost price and calculate subtotal
                    item['cost_price'] = prod.cost_price
                    subtotal += item['unit_price'] * item['quantity']

                if discount > subtotal:
                    discount = subtotal

                taxable_amount = subtotal - discount
                tax_amount = (taxable_amount * (tax_rate / Decimal('100'))).quantize(Decimal('0.01'))
                total_amount = taxable_amount + tax_amount

                # Create Sale
                sale = Sale(
                    customer=customer,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    subtotal=subtotal,
                    discount=discount,
                    tax_rate=tax_rate,
                    tax_amount=tax_amount,
                    total_amount=total_amount,
                    payment_method=payment_method,
                    notes=notes,
                    created_by=request.user,
                )
                sale.save()

                # Create items and deduct stock
                for item in items_to_process:
                    prod = locked_products[item['product_id']]
                    # Deduct stock
                    prod.quantity -= item['quantity']
                    prod.save()

                    # Audit adjustment
                    StockAdjustment.objects.create(
                        product=prod,
                        adjustment_type='REDUCE',
                        quantity=item['quantity'],
                        reason=f"Sale #{sale.invoice_number}",
                        notes=f"Sold to {sale.display_customer_name}",
                        created_by=request.user
                    )

                    # Sale item
                    SaleItem.objects.create(
                        sale=sale,
                        product=prod,
                        quantity=item['quantity'],
                        unit_price=item['unit_price'],
                        cost_price=item['cost_price'],
                        line_total=item['unit_price'] * item['quantity']
                    )

            messages.success(request, f"Sale recorded successfully! Invoice: {sale.invoice_number}")
            return redirect('sale_detail', pk=sale.pk)

        except ValueError as e:
            messages.error(request, str(e))
            return redirect('sale_create')
        except Exception as e:
            messages.error(request, f"Error completing sale: {str(e)}")
            return redirect('sale_create')

    # GET request
    customers = Customer.objects.all().order_by('name')
    products = Product.objects.all().order_by('name')

    # Pass JSON of products for fast client-side lookup
    products_data = [
        {
            'id': p.id,
            'name': p.name,
            'category': p.category,
            'selling_price': str(p.selling_price),
            'stock': p.quantity,
            'is_out_of_stock': p.is_out_of_stock,
        }
        for p in products
    ]

    return render(request, 'sales/sale_form.html', {
        'customers': customers,
        'products': products,
        'products_json': json.dumps(products_data),
        'payment_choices': Sale.PAYMENT_CHOICES,
    })


@login_required
def sale_list(request):
    """View sales history with search and date filters."""
    q = request.GET.get('q', '').strip()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    sales = Sale.objects.select_related('customer').order_by('-date', '-created_at')

    if q:
        sales = sales.filter(
            Q(invoice_number__icontains=q) |
            Q(customer__name__icontains=q) |
            Q(customer_name__icontains=q) |
            Q(customer_phone__icontains=q)
        )

    if start_date:
        sales = sales.filter(date__date__gte=start_date)
    if end_date:
        sales = sales.filter(date__date__lte=end_date)

    total_sales_amount = sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    paginator = Paginator(sales, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'sales/sale_list.html', {
        'sales': page_obj,
        'q': q,
        'start_date': start_date,
        'end_date': end_date,
        'total_sales_amount': total_sales_amount,
        'total_count': sales.count(),
    })


@login_required
def sale_detail(request, pk):
    """Detailed view of a single sale."""
    sale = get_object_or_404(Sale.objects.select_related('customer', 'created_by'), pk=pk)
    items = sale.items.select_related('product').all()
    return render(request, 'sales/sale_detail.html', {'sale': sale, 'items': items})


@login_required
def invoice_print(request, pk):
    """Printable invoice/bill view for receipt or A4 printing."""
    sale = get_object_or_404(Sale.objects.select_related('customer', 'created_by'), pk=pk)
    items = sale.items.select_related('product').all()
    return render(request, 'sales/invoice.html', {'sale': sale, 'items': items})


# ==========================================
# REPORTS
# ==========================================

@login_required
def reports_view(request):
    """Comprehensive business and sales reports."""
    preset = request.GET.get('preset', 'month')
    today = timezone.localdate()

    if preset == 'today':
        start_date = today
        end_date = today
    elif preset == 'week':
        start_date = today - timedelta(days=7)
        end_date = today
    elif preset == 'year':
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif preset == 'custom':
        s_str = request.GET.get('start_date')
        e_str = request.GET.get('end_date')
        start_date = timezone.datetime.strptime(s_str, '%Y-%m-%d').date() if s_str else (today - timedelta(days=30))
        end_date = timezone.datetime.strptime(e_str, '%Y-%m-%d').date() if e_str else today
    else:  # 'month' default
        start_date = today.replace(day=1)
        end_date = today

    # Sales in range
    sales = Sale.objects.filter(date__date__range=[start_date, end_date])

    # Aggregations
    summary = sales.aggregate(
        total_revenue=Sum('total_amount'),
        total_sales_count=Count('id'),
        total_discount=Sum('discount'),
        total_tax=Sum('tax_amount'),
    )

    revenue = summary['total_revenue'] or Decimal('0.00')
    sales_count = summary['total_sales_count'] or 0
    discount_total = summary['total_discount'] or Decimal('0.00')
    tax_total = summary['total_tax'] or Decimal('0.00')

    # Calculate profit (Revenue - Cost of items sold)
    sale_items = SaleItem.objects.filter(sale__in=sales)
    cogs_total = sum(item.cost_price * item.quantity for item in sale_items)
    estimated_profit = revenue - cogs_total

    # Daily breakdown
    daily_stats = (
        sales.annotate(sale_date=TruncDate('date'))
        .values('sale_date')
        .annotate(
            orders_count=Count('id'),
            daily_revenue=Sum('total_amount')
        )
        .order_by('-sale_date')
    )

    # Monthly breakdown for the year
    year_start = today.replace(month=1, day=1)
    monthly_stats = (
        Sale.objects.filter(date__date__gte=year_start)
        .annotate(sale_month=TruncMonth('date'))
        .values('sale_month')
        .annotate(
            orders_count=Count('id'),
            monthly_revenue=Sum('total_amount')
        )
        .order_by('-sale_month')
    )

    # Best-selling products (top 10 by quantity)
    best_sellers = (
        SaleItem.objects.filter(sale__date__date__range=[start_date, end_date])
        .values('product__id', 'product__name', 'product__category')
        .annotate(
            units_sold=Sum('quantity'),
            total_sales_val=Sum('line_total')
        )
        .order_by('-units_sold')[:10]
    )

    # Low stock report
    low_stock_products = Product.objects.filter(quantity__lte=F('low_stock_threshold')).order_by('quantity')

    context = {
        'preset': preset,
        'start_date': start_date,
        'end_date': end_date,
        'revenue': revenue,
        'sales_count': sales_count,
        'discount_total': discount_total,
        'tax_total': tax_total,
        'cogs_total': cogs_total,
        'estimated_profit': estimated_profit,
        'daily_stats': daily_stats,
        'monthly_stats': monthly_stats,
        'best_sellers': best_sellers,
        'low_stock_products': low_stock_products,
    }
    return render(request, 'reports/reports.html', context)
