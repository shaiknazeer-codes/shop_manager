"""
Re-export models from customers.models for compatibility.
"""
from customers.models import Customer, Product, StockAdjustment, Sale, SaleItem

__all__ = ['Customer', 'Product', 'StockAdjustment', 'Sale', 'SaleItem']
