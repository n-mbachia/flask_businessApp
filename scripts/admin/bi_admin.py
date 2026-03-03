#!/usr/bin/env python3
"""
Business Intelligence Admin Scripts

This module provides administrative utilities for monitoring and managing
the business intelligence system, including order analysis, system health,
and reporting capabilities.
"""
import click
import sys
from datetime import datetime, timedelta
from tabulate import tabulate

# Add project root to path
sys.path.insert(0, '..')

from app import create_app, db
from app.models import Order, Customer, OrderItem, Product, User


class AdminReporter:
    """Administrative reporting and monitoring utilities."""
    
    def __init__(self):
        self.app = create_app()
    
    def order_status_report(self, detailed=False):
        """Generate comprehensive order status report."""
        with self.app.app_context():
            # Get order counts by status
            status_counts = db.session.query(
                Order.status,
                db.func.count(Order.id),
                db.func.sum(Order.total_amount),
                db.func.avg(Order.total_amount)
            ).group_by(Order.status).all()
            
            # Prepare table data
            table_data = []
            for status, count, total, avg in status_counts:
                table_data.append([
                    status.upper(),
                    count,
                    f"${total:,.2f}" if total else "$0.00",
                    f"${avg:,.2f}" if avg else "$0.00"
                ])
            
            print("\n📊 ORDER STATUS REPORT")
            print("=" * 60)
            print(tabulate(
                table_data,
                headers=["Status", "Count", "Total Revenue", "Average Order"],
                tablefmt="grid"
            ))
            
            if detailed:
                self._detailed_orders_report()
    
    def _detailed_orders_report(self):
        """Show detailed order information."""
        print("\n📋 RECENT ORDERS (Last 10)")
        print("=" * 60)
        
        orders = Order.query.options(
            db.joinedload(Order.customer),
            db.joinedload(Order.items)
        ).order_by(Order.created_at.desc()).limit(10).all()
        
        table_data = []
        for order in orders:
            customer_name = order.customer.name if order.customer else 'No Customer'
            table_data.append([
                order.id,
                order.order_number or 'N/A',
                order.status.upper(),
                customer_name,
                order.created_at.strftime('%Y-%m-%d %H:%M'),
                len(order.items),
                f"${order.total_amount:,.2f}"
            ])
        
        print(tabulate(
            table_data,
            headers=["ID", "Order #", "Status", "Customer", "Date", "Items", "Total"],
            tablefmt="grid"
        ))
    
    def customer_analysis(self):
        """Generate customer analysis report."""
        with self.app.app_context():
            print("\n👥 CUSTOMER ANALYSIS")
            print("=" * 60)
            
            # Top customers by revenue
            top_customers = db.session.query(
                Customer.id,
                Customer.name,
                Customer.email,
                db.func.sum(Order.total_amount).label('total_spent'),
                db.func.count(Order.id).label('order_count')
            ).join(Order).group_by(Customer.id).order_by(
                db.desc('total_spent')
            ).limit(10).all()
            
            table_data = []
            for customer_id, name, email, total_spent, order_count in top_customers:
                table_data.append([
                    customer_id,
                    name[:30] + '...' if len(name) > 30 else name,
                    email[:25] + '...' if len(email) > 25 else email,
                    f"${total_spent:,.2f}",
                    order_count
                ])
            
            print("\n🏆 TOP 10 CUSTOMERS BY REVENUE")
            print("-" * 40)
            print(tabulate(
                table_data,
                headers=["ID", "Name", "Email", "Total Spent", "Orders"],
                tablefmt="grid"
            ))
    
    def product_performance(self):
        """Generate product performance report."""
        with self.app.app_context():
            print("\n📦 PRODUCT PERFORMANCE")
            print("=" * 60)
            
            # Top products by revenue
            top_products = db.session.query(
                Product.id,
                Product.name,
                Product.sku,
                db.func.sum(OrderItem.quantity).label('total_sold'),
                db.func.sum(OrderItem.subtotal).label('total_revenue')
            ).join(OrderItem).group_by(Product.id).order_by(
                db.desc('total_revenue')
            ).limit(10).all()
            
            table_data = []
            for product_id, name, sku, total_sold, total_revenue in top_products:
                table_data.append([
                    product_id,
                    name[:30] + '...' if len(name) > 30 else name,
                    sku or 'N/A',
                    int(total_sold) if total_sold else 0,
                    f"${total_revenue:,.2f}" if total_revenue else "$0.00"
                ])
            
            print("\n🥇 TOP 10 PRODUCTS BY REVENUE")
            print("-" * 40)
            print(tabulate(
                table_data,
                headers=["ID", "Name", "SKU", "Units Sold", "Revenue"],
                tablefmt="grid"
            ))
    
    def system_health(self):
        """Generate system health report."""
        with self.app.app_context():
            print("\n🏥 SYSTEM HEALTH REPORT")
            print("=" * 60)
            
            # Database statistics
            stats = {
                'Total Orders': Order.query.count(),
                'Total Customers': Customer.query.count(),
                'Total Products': Product.query.count(),
                'Total Users': User.query.count(),
                'Completed Orders': Order.query.filter_by(status='completed').count(),
                'Pending Orders': Order.query.filter_by(status='pending').count(),
                'Cancelled Orders': Order.query.filter_by(status='cancelled').count(),
            }
            
            # Calculate revenue metrics
            total_revenue = db.session.query(
                db.func.sum(Order.total_amount)
            ).filter_by(status='completed').scalar() or 0
            
            avg_order_value = db.session.query(
                db.func.avg(Order.total_amount)
            ).filter_by(status='completed').scalar() or 0
            
            stats['Total Revenue'] = f"${total_revenue:,.2f}"
            stats['Avg Order Value'] = f"${avg_order_value:,.2f}"
            
            # Display as table
            table_data = [[key, value] for key, value in stats.items()]
            print(tabulate(
                table_data,
                headers=["Metric", "Value"],
                tablefmt="grid"
            ))
    
    def recent_activity(self, days=7):
        """Show recent activity for specified days."""
        with self.app.app_context():
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            print(f"\n📈 RECENT ACTIVITY (Last {days} days)")
            print("=" * 60)
            
            # Recent orders
            recent_orders = Order.query.filter(
                Order.created_at >= cutoff_date
            ).order_by(Order.created_at.desc()).limit(20).all()
            
            if recent_orders:
                table_data = []
                for order in recent_orders:
                    customer_name = order.customer.name if order.customer else 'No Customer'
                    table_data.append([
                        order.id,
                        order.status.upper(),
                        customer_name,
                        order.created_at.strftime('%Y-%m-%d %H:%M'),
                        f"${order.total_amount:,.2f}"
                    ])
                
                print(tabulate(
                    table_data,
                    headers=["ID", "Status", "Customer", "Date", "Total"],
                    tablefmt="grid"
                ))
            else:
                print(f"No orders found in the last {days} days.")


# CLI Interface
@click.group()
def cli():
    """Business Intelligence Admin CLI"""
    pass


@cli.command()
@click.option('--detailed', '-d', is_flag=True, help='Show detailed order information')
def orders(detailed):
    """Generate order status report"""
    reporter = AdminReporter()
    reporter.order_status_report(detailed=detailed)


@cli.command()
def customers():
    """Generate customer analysis report"""
    reporter = AdminReporter()
    reporter.customer_analysis()


@cli.command()
def products():
    """Generate product performance report"""
    reporter = AdminReporter()
    reporter.product_performance()


@cli.command()
def health():
    """Generate system health report"""
    reporter = AdminReporter()
    reporter.system_health()


@cli.command()
@click.option('--days', '-d', default=7, help='Number of days to look back')
def activity(days):
    """Show recent activity"""
    reporter = AdminReporter()
    reporter.recent_activity(days=days)


@cli.command()
def dashboard():
    """Generate comprehensive dashboard report"""
    reporter = AdminReporter()
    reporter.order_status_report(detailed=False)
    reporter.customer_analysis()
    reporter.product_performance()
    reporter.system_health()
    reporter.recent_activity(days=7)


if __name__ == '__main__':
    cli()
