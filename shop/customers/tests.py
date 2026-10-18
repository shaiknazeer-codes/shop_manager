from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from .models import Customer, Product, StockAdjustment, Sale, SaleItem


class ShopManagerTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='TestPassword123!',
            email='testuser@example.com'
        )
        self.client = Client()

        # Create test customer
        self.customer = Customer.objects.create(
            name='Alice Wonderland',
            phone='1234567890',
            email='alice@example.com',
            address='123 Rabbit Hole Way'
        )

        # Create test products
        self.product1 = Product.objects.create(
            name='Wireless Mouse',
            category='Electronics',
            cost_price=Decimal('15.00'),
            selling_price=Decimal('25.00'),
            quantity=20,
            low_stock_threshold=5,
            description='Ergonomic wireless mouse'
        )

        self.product2 = Product.objects.create(
            name='Mechanical Keyboard',
            category='Electronics',
            cost_price=Decimal('40.00'),
            selling_price=Decimal('75.00'),
            quantity=4,  # Below threshold 5 -> low stock!
            low_stock_threshold=5,
            description='RGB mechanical keyboard'
        )

    # -------------------------------------------------------------------------
    # Authentication & Access Control Tests
    # -------------------------------------------------------------------------
    def test_unauthenticated_redirect(self):
        """Unauthenticated requests should be redirected to login."""
        protected_urls = [
            reverse('dashboard'),
            reverse('product_list'),
            reverse('customer_list'),
            reverse('inventory_list'),
            reverse('sale_list'),
            reverse('reports'),
            reverse('sale_create'),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith(reverse('login')))

    def test_authenticated_access(self):
        """Authenticated users can access the dashboard and lists."""
        self.client.login(username='testuser', password='TestPassword123!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome back')

    # -------------------------------------------------------------------------
    # Product CRUD Tests
    # -------------------------------------------------------------------------
    def test_product_model_properties(self):
        """Test Product margin, stock status, and low stock calculations."""
        self.assertEqual(self.product1.margin, Decimal('10.00'))
        self.assertFalse(self.product1.is_low_stock)
        self.assertEqual(self.product1.stock_status, 'In Stock')

        # product2 has quantity 4 and threshold 5
        self.assertTrue(self.product2.is_low_stock)
        self.assertEqual(self.product2.stock_status, 'Low Stock')

        self.product2.quantity = 0
        self.product2.save()
        self.assertTrue(self.product2.is_out_of_stock)
        self.assertEqual(self.product2.stock_status, 'Out of Stock')

    def test_product_create_and_validation(self):
        """Test creating product via view and server-side validation."""
        self.client.login(username='testuser', password='TestPassword123!')
        response = self.client.post(reverse('product_create'), {
            'name': 'USB-C Cable',
            'category': 'Electronics',
            'cost_price': '4.50',
            'selling_price': '9.99',
            'quantity': '50',
            'low_stock_threshold': '10',
            'description': 'High speed cable'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(name='USB-C Cable').exists())

    def test_product_negative_validation(self):
        """Test that negative quantities and prices are rejected."""
        self.client.login(username='testuser', password='TestPassword123!')
        response = self.client.post(reverse('product_create'), {
            'name': 'Invalid Product',
            'category': 'Test',
            'cost_price': '-5.00',
            'selling_price': '10.00',
            'quantity': '-1',
            'low_stock_threshold': '5'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.filter(name='Invalid Product').exists())

    # -------------------------------------------------------------------------
    # Customer CRUD Tests
    # -------------------------------------------------------------------------
    def test_customer_creation_and_search(self):
        """Test customer creation and search functionality."""
        self.client.login(username='testuser', password='TestPassword123!')
        response = self.client.post(reverse('customer_create'), {
            'name': 'Bob Builder',
            'phone': '9876543210',
            'email': 'bob@example.com',
            'address': 'Fixit Avenue'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Customer.objects.filter(name='Bob Builder').exists())

        # Search
        search_res = self.client.get(reverse('customer_list') + '?q=Builder')
        self.assertContains(search_res, 'Bob Builder')

    # -------------------------------------------------------------------------
    # Inventory & Stock Adjustment Tests
    # -------------------------------------------------------------------------
    def test_stock_adjustment_add_and_reduce(self):
        """Test adding and reducing stock via StockAdjustment."""
        self.client.login(username='testuser', password='TestPassword123!')

        # Add stock (+10)
        response = self.client.post(reverse('stock_adjust'), {
            'product_id': self.product1.id,
            'adjustment_type': 'ADD',
            'quantity': '10',
            'reason_choice': 'Received Shipment',
            'notes': 'Restocked from supplier'
        })
        self.assertEqual(response.status_code, 302)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.quantity, 30)

        # Reduce stock (-5)
        response = self.client.post(reverse('stock_adjust'), {
            'product_id': self.product1.id,
            'adjustment_type': 'REDUCE',
            'quantity': '5',
            'reason_choice': 'Damaged / Expired',
            'notes': 'Damaged box'
        })
        self.assertEqual(response.status_code, 302)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.quantity, 25)

    def test_stock_adjustment_prevent_negative(self):
        """Stock reduction exceeding available inventory should fail."""
        self.client.login(username='testuser', password='TestPassword123!')
        response = self.client.post(reverse('stock_adjust'), {
            'product_id': self.product1.id,
            'adjustment_type': 'REDUCE',
            'quantity': '999',  # More than 20
            'reason_choice': 'Loss / Theft',
        })
        self.assertEqual(response.status_code, 302)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.quantity, 20)  # Unchanged!

    # -------------------------------------------------------------------------
    # Sales & Billing Tests
    # -------------------------------------------------------------------------
    def test_sale_creation_and_stock_deduction(self):
        """Test creating a multi-product sale and ensuring atomic stock deduction."""
        self.client.login(username='testuser', password='TestPassword123!')

        initial_p1_stock = self.product1.quantity  # 20
        initial_p2_stock = self.product2.quantity  # 4

        response = self.client.post(reverse('sale_create'), {
            'customer': self.customer.id,
            'customer_name': self.customer.name,
            'customer_phone': self.customer.phone,
            'payment_method': 'Cash',
            'discount': '5.00',
            'tax_rate': '10.0',
            'notes': 'Test sale transaction',
            'product_id[]': [self.product1.id, self.product2.id],
            'quantity[]': ['2', '1'],
            'unit_price[]': ['25.00', '75.00'],
        })
        self.assertEqual(response.status_code, 302)

        # Verify sale was saved
        sale = Sale.objects.filter(customer=self.customer).first()
        self.assertIsNotNone(sale)
        self.assertTrue(sale.invoice_number.startswith('INV-'))

        # Subtotal: (2 * 25.00) + (1 * 75.00) = 50.00 + 75.00 = 125.00
        self.assertEqual(sale.subtotal, Decimal('125.00'))
        self.assertEqual(sale.discount, Decimal('5.00'))
        # Taxable: 125 - 5 = 120.00. 10% tax = 12.00. Total = 132.00
        self.assertEqual(sale.tax_amount, Decimal('12.00'))
        self.assertEqual(sale.total_amount, Decimal('132.00'))

        # Verify stock was deducted
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.quantity, initial_p1_stock - 2)
        self.assertEqual(self.product2.quantity, initial_p2_stock - 1)

    def test_sale_insufficient_stock_rejection(self):
        """Sale should be aborted and rejected if requested quantity exceeds stock."""
        self.client.login(username='testuser', password='TestPassword123!')

        initial_p2_stock = self.product2.quantity  # 4

        response = self.client.post(reverse('sale_create'), {
            'customer_name': 'Walk-in Customer',
            'payment_method': 'Cash',
            'discount': '0.00',
            'tax_rate': '0.00',
            'product_id[]': [self.product2.id],
            'quantity[]': ['10'],  # 10 > 4!
            'unit_price[]': ['75.00'],
        })
        self.assertEqual(response.status_code, 302)

        # No sale should have been created
        self.assertEqual(Sale.objects.count(), 0)

        # Stock should remain untouched
        self.product2.refresh_from_db()
        self.assertEqual(self.product2.quantity, initial_p2_stock)

    def test_walk_in_customer_sale(self):
        """Test sale for a walk-in customer without selecting a registered customer."""
        self.client.login(username='testuser', password='TestPassword123!')

        response = self.client.post(reverse('sale_create'), {
            'customer': '',
            'customer_name': 'Random Walk-in',
            'customer_phone': '555-1234',
            'payment_method': 'UPI',
            'discount': '0.00',
            'tax_rate': '0.00',
            'product_id[]': [self.product1.id],
            'quantity[]': ['1'],
            'unit_price[]': ['25.00'],
        })
        self.assertEqual(response.status_code, 302)

        sale = Sale.objects.filter(customer_name='Random Walk-in').first()
        self.assertIsNotNone(sale)
        self.assertIsNone(sale.customer)
        self.assertEqual(sale.display_customer_name, 'Random Walk-in')

    # -------------------------------------------------------------------------
    # Reports Test
    # -------------------------------------------------------------------------
    def test_reports_page_calculation(self):
        """Test reports page renders accurate metrics."""
        self.client.login(username='testuser', password='TestPassword123!')

        # Make a sale
        Sale.objects.create(
            customer=self.customer,
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            date=timezone.now()
        )

        response = self.client.get(reverse('reports') + '?preset=today')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '100.00')
