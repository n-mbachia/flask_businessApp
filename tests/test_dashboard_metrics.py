import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from mn_venturesApp.businessApp.tests.dashboard_metrics import DashboardMetrics, PerformanceAnalyzer
from app import db
from app.models import Product, Sales, Costs, User

class TestDashboardMetrics(unittest.TestCase):    
    def setUp(self):
        """Set up test data and mocks."""
        self.user_id = 1
        self.dm = DashboardMetrics(user_id=self.user_id)
        
        # Sample data for testing
        self.sample_products = [
            Product(id=1, user_id=1, name="Product 1", 
                   selling_price_per_unit=10.0, 
                   cogs_per_unit=5.0,
                   margin_threshold=20.0),
            Product(id=2, user_id=1, name="Product 2",
                   selling_price_per_unit=15.0,
                   cogs_per_unit=7.0,
                   margin_threshold=25.0)
        ]
        
        # Mock datetime for consistent testing
        self.now = datetime.utcnow()
        self.last_month = self.now - timedelta(days=30)
        
    def tearDown(self):
        """Clean up after each test."""
        pass

    def test_calculate_start_date_week(self):
        """Test _calculate_start_date with 'week' period."""
        result = self.dm._calculate_start_date(self.now, 'week')
        expected = self.now - timedelta(days=7)
        self.assertEqual(result.date(), expected.date())
        
    def test_calculate_start_date_invalid_period(self):
        """Test _calculate_start_date with invalid period."""
        result = self.dm._calculate_start_date(self.now, 'invalid')
        expected = self.now - timedelta(days=30)  # Default fallback
        self.assertEqual(result.date(), expected.date())
    
    @patch('app.dashboard_metrics.db.session.query')
    def test_calculate_metrics_no_products(self, mock_query):
        """Test _calculate_metrics when no products exist."""
        # Mock Product query to return empty list
        mock_product_query = MagicMock()
        mock_product_query.all.return_value = []
        
        # Mock the query chain
        mock_query.return_value = MagicMock()
        mock_query.return_value.filter_by.return_value = mock_product_query
        
        result = self.dm._calculate_metrics(self.last_month, self.now)
        self.assertIsNone(result)
    
    @patch('app.dashboard_metrics.db.session.query')
    def test_calculate_metrics_with_data(self, mock_query):
        """Test _calculate_metrics with sample sales and costs data."""
        # Mock Product query
        mock_product_query = MagicMock()
        mock_product_query.all.return_value = self.sample_products
        
        # Mock Sales query
        mock_sales = MagicMock()
        mock_sales.first.return_value = MagicMock(revenue=1000.0, cogs=500.0)
        
        # Mock Costs query
        mock_costs = MagicMock()
        mock_costs.first.return_value = MagicMock(total_costs=200.0)
        
        # Mock User/Product threshold query
        mock_threshold = MagicMock()
        mock_threshold.scalar.return_value = 20.0
        
        # Set up the query chain
        mock_query.side_effect = [
            mock_product_query,  # First call - Products
            mock_sales,         # Second call - Sales
            mock_costs,         # Third call - Costs
            mock_threshold      # Fourth call - Threshold
        ]
        
        result = self.dm._calculate_metrics(self.last_month, self.now)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['revenue'], 1000.0)
        self.assertEqual(result['cogs'], 500.0)
        self.assertEqual(result['total_costs'], 200.0)
        self.assertEqual(result['profit'], 300.0)  # 1000 - 500 - 200
        self.assertEqual(result['margin'], 30.0)   # (300 / 1000) * 100
        self.assertFalse(result['alert'])  # 30% > 20% threshold
    
    def test_get_comparison_data_previous_period(self):
        """Test _get_comparison_data with 'previous_period' comparison."""
        with patch.object(self.dm, '_calculate_metrics') as mock_calc:
            mock_calc.return_value = {'revenue': 1000.0}
            
            result = self.dm._get_comparison_data(
                start_date=self.now - timedelta(days=30),
                end_date=self.now,
                comparison_type='previous_period'
            )
            
            self.assertEqual(result, {'revenue': 1000.0})
            mock_calc.assert_called_once()
    
    def test_get_targets(self):
        """Test _get_targets method."""
        with patch.object(self.dm, '_calculate_metrics') as mock_calc:
            mock_calc.return_value = {
                'revenue': 1000.0,
                'cogs': 500.0,
                'profit': 300.0,
                'margin': 30.0,
                'total_costs': 200.0
            }
            
            result = self.dm._get_targets()
            
            # Check if targets are calculated correctly with class constants
            self.assertAlmostEqual(result['revenue'], 1100.0)  # +10%
            self.assertAlmostEqual(result['cogs'], 475.0)      # -5%
            self.assertAlmostEqual(result['profit'], 345.0)     # +15%
            self.assertAlmostEqual(result['margin'], 31.5)      # +5%
            self.assertAlmostEqual(result['total_costs'], 190.0) # -5%


class TestPerformanceAnalyzer(unittest.TestCase):
    def setUp(self):
        """Set up test data for PerformanceAnalyzer tests."""
        # Sample metric data for trend analysis
        self.sample_metric_data = {
            'months': [f'2023-{m:02d}' for m in range(1, 13)],  # Jan-Dec 2023
            'values': [100 + i*10 for i in range(12)]  # 100, 110, 120, ..., 210
        }
        
    def test_calculate_trends_insufficient_data(self):
        """Test calculate_trends with insufficient data."""
        result = PerformanceAnalyzer.calculate_trends(
            {'months': [], 'values': []}
        )
        self.assertIn('error', result)
        self.assertEqual(result['min_required'], 3)
    
    def test_calculate_trends_success(self):
        """Test calculate_trends with valid data."""
        result = PerformanceAnalyzer.calculate_trends(self.sample_metric_data)
        
        self.assertIn('trend', result)
        self.assertIn('model_metrics', result)
        self.assertIn('r2_score', result['model_metrics'])
        self.assertIn('mae', result['model_metrics'])
        self.assertIn('moving_avg', result)
        
        # Since our sample data is strictly increasing, trend should be 'up'
        self.assertEqual(result['trend'], 'up')
        
        # R² should be close to 1 for our perfect linear data
        self.assertGreater(result['model_metrics']['r2_score'], 0.9)
    
    @patch('app.dashboard_metrics.db.session.query')
    def test_generate_forecast_insufficient_data(self, mock_query):
        """Test generate_forecast with insufficient historical data."""
        # Mock the query to return minimal data
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(month='2023-01', revenue=100.0),
            MagicMock(month='2023-02', revenue=110.0)
        ]
        mock_query.return_value = mock_result
        
        result = PerformanceAnalyzer.generate_forecast(user_id=1)
        
        self.assertEqual(result['status'], 'error')
        self.assertIn('Insufficient historical data', result['error'])
        self.assertEqual(result['min_required'], 6)
    
    @patch('app.dashboard_metrics.db.session.query')
    def test_generate_forecast_success(self, mock_query):
        """Test generate_forecast with sufficient data."""
        # Create a year of monthly increasing data
        months = [f'2023-{m:02d}' for m in range(1, 13)]
        values = [100 + i*10 for i in range(12)]
        
        # Mock the query to return the test data
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(month=m, revenue=v) for m, v in zip(months, values)
        ]
        mock_query.return_value = mock_result
        
        result = PerformanceAnalyzer.generate_forecast(user_id=1, forecast_months=3)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['forecast']), 3)
        self.assertEqual(len(result['forecast_dates']), 3)
        self.assertIn('model_metrics', result)
        self.assertIn('r2_score', result['model_metrics'])
        self.assertIn('mae', result['model_metrics'])
        self.assertIn('rmse', result['model_metrics'])
        
        # For our increasing data, forecast should be increasing
        self.assertLess(result['forecast'][0], result['forecast'][1])
        self.assertLess(result['forecast'][1], result['forecast'][2])


if __name__ == '__main__':
    unittest.main()
