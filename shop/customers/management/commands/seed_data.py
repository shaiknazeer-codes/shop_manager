from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from customers.models import Customer, Product, Sale, SaleItem, StockAdjustment


class Command(BaseCommand):
    help = 'Seeds initial sample products, customers, and sales for demonstration.'

    def handle(self, *args, **options):
        self.stdout.write("Seeding sample data...")

        # Ensure demo user
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.create_user(username='admin', password='adminpassword123', is_staff=True, is_superuser=True)
            self.stdout.write("Created default superuser: admin / adminpassword123")

        # Create sample customers
        c1, _ = Customer.objects.get_or_create(
            name='Sarah Jenkins',
            phone='555-0144',
            email='sarah.j@example.com',
            address='742 Evergreen Terrace, Springfield'
        )
        c2, _ = Customer.objects.get_or_create(
            name='Michael Chang',
            phone='555-0182',
            email='mchang@example.com',
            address='1204 Elm Street, Apt 3B'
        )
        c3, _ = Customer.objects.get_or_create(
            name='Elena Rostova',
            phone='555-0199',
            email='elena.r@example.com',
            address='480 Baker Road, Metroville'
        )

        # Create sample products
        products_data = [
            {'name': 'Logitech Wireless Mouse M185', 'category': 'Electronics', 'cost_price': Decimal('12.00'), 'selling_price': Decimal('22.99'), 'quantity': 28, 'low_stock_threshold': 8, 'description': 'Reliable plug-and-play wireless mouse'},
            {'name': 'USB-C Fast Charging Cable 2M', 'category': 'Electronics', 'cost_price': Decimal('3.50'), 'selling_price': Decimal('9.99'), 'quantity': 45, 'low_stock_threshold': 10, 'description': 'Braided nylon 60W charging cable'},
            {'name': 'Mechanical Gaming Keyboard RGB', 'category': 'Electronics', 'cost_price': Decimal('38.00'), 'selling_price': Decimal('69.99'), 'quantity': 4, 'low_stock_threshold': 6, 'description': 'Blue switches with custom backlighting'},
            {'name': 'Premium Cotton T-Shirt (Navy, L)', 'category': 'Clothing', 'cost_price': Decimal('8.00'), 'selling_price': Decimal('19.50'), 'quantity': 32, 'low_stock_threshold': 10, 'description': '100% combed ringspun cotton'},
            {'name': 'Ceramic Coffee Mug (12oz)', 'category': 'Home & Kitchen', 'cost_price': Decimal('4.20'), 'selling_price': Decimal('11.00'), 'quantity': 18, 'low_stock_threshold': 5, 'description': 'Matte finish heat-resistant mug'},
            {'name': 'Hardcover Ruled Notebook A5', 'category': 'Stationery', 'cost_price': Decimal('2.80'), 'selling_price': Decimal('6.50'), 'quantity': 50, 'low_stock_threshold': 12, 'description': '160 pages acid-free paper'},
            {'name': 'Organic Green Tea (Box of 50)', 'category': 'Groceries', 'cost_price': Decimal('5.50'), 'selling_price': Decimal('12.00'), 'quantity': 3, 'low_stock_threshold': 10, 'description': 'Pure Ceylon organic loose leaf teabags'},
            {'name': 'Bluetooth Noise Canceling Earbuds', 'category': 'Electronics', 'cost_price': Decimal('28.00'), 'selling_price': Decimal('54.99'), 'quantity': 0, 'low_stock_threshold': 5, 'description': 'Wireless earbuds with charging case'},
        ]

        created_prods = []
        for p_data in products_data:
            p, _ = Product.objects.get_or_create(name=p_data['name'], defaults=p_data)
            created_prods.append(p)

        # Create a sample sale
        if Sale.objects.count() == 0:
            p1 = created_prods[0]  # Mouse
            p2 = created_prods[1]  # Cable

            sale = Sale.objects.create(
                customer=c1,
                customer_name=c1.name,
                customer_phone=c1.phone,
                date=timezone.now(),
                subtotal=p1.selling_price + (p2.selling_price * 2),
                discount=Decimal('2.00'),
                tax_rate=Decimal('5.0'),
                payment_method='Card',
                notes='Online store pickup',
                created_by=user
            )
            taxable = sale.subtotal - sale.discount
            sale.tax_amount = (taxable * Decimal('0.05')).quantize(Decimal('0.01'))
            sale.total_amount = taxable + sale.tax_amount
            sale.save()

            SaleItem.objects.create(
                sale=sale,
                product=p1,
                quantity=1,
                unit_price=p1.selling_price,
                cost_price=p1.cost_price,
                line_total=p1.selling_price
            )
            SaleItem.objects.create(
                sale=sale,
                product=p2,
                quantity=2,
                unit_price=p2.selling_price,
                cost_price=p2.cost_price,
                line_total=p2.selling_price * 2
            )

        self.stdout.write(self.style.SUCCESS("Sample data successfully loaded!"))
