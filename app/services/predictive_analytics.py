"""
Predictive Analytics Service for business intelligence and forecasting.
"""
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import pandas as pd
import logging

from app import db
from app.models import Order, OrderItem, Product, Customer
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

@dataclass
class ForecastResult:
    """Container for forecast results."""
    predictions: List[float]
    confidence_intervals: List[Tuple[float, float]]
    accuracy_score: float
    trend_direction: str
    seasonality_detected: bool
    recommendations: List[str]

@dataclass
class CustomerSegment:
    """Customer segmentation data."""
    segment: str
    count: int
    avg_lifetime_value: float
    avg_order_frequency: float
    churn_risk: float
    recommendations: List[str]

class PredictiveAnalytics:
    """Service for predictive analytics and business intelligence."""
    
    @staticmethod
    def forecast_revenue(
        user_id: int, 
        periods: int = 12,
        confidence_level: float = 0.95
    ) -> ForecastResult:
        """
        Forecast revenue using linear regression with confidence intervals.
        
        Args:
            user_id: User to forecast for
            periods: Number of future periods to predict
            confidence_level: Confidence interval level (0.8, 0.9, 0.95)
            
        Returns:
            ForecastResult with predictions and insights
        """
        try:
            # Get historical data (last 24 months for better accuracy)
            historical_data = AnalyticsService.get_sales_by_month(
                user_id=user_id, limit=24
            )
            
            if len(historical_data) < 3:
                return PredictiveAnalytics._create_insufficient_data_forecast()
            
            # Prepare data for ML
            df = pd.DataFrame(historical_data)
            df['date'] = pd.to_datetime(df['year'].astype(str) + '-' + df['month'].astype(str) + '-01')
            df['period'] = range(len(df))
            
            # Feature engineering
            X = df[['period']].values
            y = df['total_revenue'].values
            
            # Train model
            model = LinearRegression()
            model.fit(X, y)
            
            # Make predictions
            future_periods = np.array(range(len(df), len(df) + periods)).reshape(-1, 1)
            predictions = model.predict(future_periods)
            
            # Calculate confidence intervals
            residuals = y - model.predict(X)
            mse = np.mean(residuals ** 2)
            std_error = np.sqrt(mse)
            
            # Z-score for confidence interval
            z_scores = {0.8: 1.28, 0.9: 1.645, 0.95: 1.96}
            z = z_scores.get(confidence_level, 1.96)
            
            margin_of_error = z * std_error
            confidence_intervals = [
                (max(0, pred - margin_of_error), pred + margin_of_error)
                for pred in predictions
            ]
            
            # Calculate accuracy
            y_pred = model.predict(X)
            accuracy = 1 - (mean_absolute_error(y, y_pred) / np.mean(y))
            
            # Detect trend
            trend_direction = 'stable'
            if len(predictions) > 1:
                trend_change = (predictions[-1] - predictions[0]) / predictions[0]
                if trend_change > 0.05:
                    trend_direction = 'increasing'
                elif trend_change < -0.05:
                    trend_direction = 'decreasing'
            
            # Detect seasonality (simplified)
            seasonality_detected = PredictiveAnalytics._detect_seasonality(df['total_revenue'].values)
            
            # Generate recommendations
            recommendations = PredictiveAnalytics._generate_revenue_recommendations(
                predictions, trend_direction, accuracy
            )
            
            return ForecastResult(
                predictions=predictions.tolist(),
                confidence_intervals=confidence_intervals,
                accuracy_score=accuracy,
                trend_direction=trend_direction,
                seasonality_detected=seasonality_detected,
                recommendations=recommendations
            )
            
        except Exception as e:
            try:
                logger.error(f"Error forecasting revenue: {str(e)}")
            except NameError:
                logging.getLogger(__name__).error(f"Error forecasting revenue: {str(e)}")
            return PredictiveAnalytics._create_error_forecast()
    
    @staticmethod
    def detect_anomalies(user_id: int, metric: str = 'revenue', threshold: float = 2.0) -> List[Dict[str, Any]]:
        """
        Detect statistical anomalies in business metrics.
        
        Args:
            user_id: User to analyze
            metric: Metric to analyze ('revenue', 'orders', 'customers')
            threshold: Standard deviation threshold for anomaly detection
            
        Returns:
            List of detected anomalies with details
        """
        try:
            # Get historical data
            historical_data = AnalyticsService.get_sales_by_month(user_id=user_id, limit=24)
            
            if len(historical_data) < 6:
                return []
            
            # Extract metric data
            if metric == 'revenue':
                values = [float(row['total_revenue']) for row in historical_data]
            elif metric == 'orders':
                values = [int(row['order_count']) for row in historical_data]
            else:
                values = [int(row['customer_count']) for row in historical_data]
            
            # Calculate statistics
            mean_val = np.mean(values)
            std_val = np.std(values)
            
            # Detect anomalies
            anomalies = []
            for i, value in enumerate(historical_data):
                metric_value = values[i]
                z_score = abs((metric_value - mean_val) / std_val) if std_val > 0 else 0
                
                if z_score > threshold:
                    anomaly_type = 'spike' if metric_value > mean_val else 'drop'
                    
                    anomalies.append({
                        'date': f"{value['year']}-{value['month']:02d}",
                        'metric': metric,
                        'value': metric_value,
                        'expected': mean_val,
                        'z_score': z_score,
                        'severity': 'high' if z_score > 3 else 'medium',
                        'type': anomaly_type,
                        'description': f'{anomaly_type.title()} detected: {metric} was {z_score:.1f}x standard deviations from normal'
                    })
            
            return anomalies
            
        except Exception as e:
            try:
                logger.error(f"Error detecting anomalies: {str(e)}")
            except NameError:
                logging.getLogger(__name__).error(f"Error detecting anomalies: {str(e)}")
            return []
    
    @staticmethod
    def customer_segmentation(user_id: int) -> List[CustomerSegment]:
        """
        Perform RFM (Recency, Frequency, Monetary) customer segmentation.
        
        Args:
            user_id: User to analyze
            
        Returns:
            List of customer segments with insights
        """
        def _default_segments() -> List[CustomerSegment]:
            segment_objects = []
            for segment_name in ['Champions', 'Loyal Customers', 'At Risk', 'Lost', 'New']:
                segment_objects.append(CustomerSegment(
                    segment=segment_name,
                    count=0,
                    avg_lifetime_value=0.0,
                    avg_order_frequency=0.0,
                    churn_risk=0.0,
                    recommendations=PredictiveAnalytics._generate_segment_recommendations(segment_name, 0)
                ))
            return segment_objects

        try:
            # Get customer sales data
            customer_data = AnalyticsService.get_customer_sales(user_id=user_id, limit=100)
            
            if not customer_data:
                return _default_segments()
            
            # Calculate RFM scores
            customers = []
            for customer in customer_data:
                # Recency score (days since last order)
                last_order_date = customer.get('last_order_date')
                if last_order_date:
                    last_order = datetime.strptime(last_order_date, '%Y-%m-%d').date()
                    recency_days = (date.today() - last_order).days
                else:
                    recency_days = 365  # Assume very old
                
                # Frequency score
                frequency = customer.get('order_count', 0)
                
                # Monetary score
                monetary = float(customer.get('total_spent', 0))
                
                customers.append({
                    'customer_id': customer.get('customer_id'),
                    'recency_days': recency_days,
                    'frequency': frequency,
                    'monetary': monetary
                })
            
            if not customers:
                return _default_segments()
            
            # Calculate percentiles for scoring
            recency_scores = [c['recency_days'] for c in customers]
            frequency_scores = [c['frequency'] for c in customers]
            monetary_scores = [c['monetary'] for c in customers]
            
            # Create segments
            segments = {
                'Champions': [],
                'Loyal Customers': [],
                'At Risk': [],
                'Lost': [],
                'New': []
            }
            
            for customer in customers:
                # Simple RFM scoring
                recency_score = 5 - (customer['recency_days'] // 30)  # Lower days = higher score
                recency_score = max(1, min(5, recency_score))
                
                frequency_score = min(5, customer['frequency'] // 2)  # More orders = higher score
                frequency_score = max(1, frequency_score)
                
                monetary_score = min(5, customer['monetary'] // 100)  # More spent = higher score
                monetary_score = max(1, monetary_score)
                
                # Segment based on RFM scores
                if recency_score >= 4 and frequency_score >= 4 and monetary_score >= 4:
                    segment = 'Champions'
                elif recency_score >= 3 and frequency_score >= 3:
                    segment = 'Loyal Customers'
                elif recency_score >= 2 and frequency_score >= 2:
                    segment = 'At Risk'
                elif recency_score <= 2 and frequency_score <= 2:
                    segment = 'Lost'
                else:
                    segment = 'New'
                
                segments[segment].append(customer)
            
            # Create segment objects with insights
            segment_objects = []
            for segment_name, segment_customers in segments.items():
                if not segment_customers:
                    continue
                
                avg_ltv = np.mean([c['monetary'] for c in segment_customers])
                avg_frequency = np.mean([c['frequency'] for c in segment_customers])
                
                # Calculate churn risk
                if segment_name == 'Champions':
                    churn_risk = 0.1
                elif segment_name == 'Loyal Customers':
                    churn_risk = 0.2
                elif segment_name == 'At Risk':
                    churn_risk = 0.6
                elif segment_name == 'Lost':
                    churn_risk = 0.9
                else:  # New
                    churn_risk = 0.4
                
                recommendations = PredictiveAnalytics._generate_segment_recommendations(
                    segment_name, len(segment_customers)
                )
                
                segment_objects.append(CustomerSegment(
                    segment=segment_name,
                    count=len(segment_customers),
                    avg_lifetime_value=avg_ltv,
                    avg_order_frequency=avg_frequency,
                    churn_risk=churn_risk,
                    recommendations=recommendations
                ))
            
            return segment_objects
            
        except Exception as e:
            try:
                logger.error(f"Error in customer segmentation: {str(e)}")
            except NameError:
                logging.getLogger(__name__).error(f"Error in customer segmentation: {str(e)}")
            return _default_segments()
    
    @staticmethod
    def generate_business_insights(user_id: int) -> Dict[str, Any]:
        """
        Generate comprehensive business insights and recommendations.
        
        Args:
            user_id: User to analyze
            
        Returns:
            Dictionary with insights and actionable recommendations
        """
        try:
            insights = {
                'revenue_insights': [],
                'customer_insights': [],
                'product_insights': [],
                'operational_insights': [],
                'growth_opportunities': [],
                'risk_alerts': []
            }
            
            # Revenue insights
            forecast = PredictiveAnalytics.forecast_revenue(user_id, periods=6)
            if forecast.accuracy_score > 0.7:
                insights['revenue_insights'].append({
                    'type': 'trend',
                    'title': 'Revenue Trend Analysis',
                    'description': f'Revenue is {forecast.trend_direction} with {forecast.accuracy_score:.1%} forecast accuracy',
                    'recommendation': 'Focus on growth strategies' if forecast.trend_direction == 'increasing' else 'Investigate revenue decline'
                })
            
            # Customer insights
            segments = PredictiveAnalytics.customer_segmentation(user_id)
            if segments:
                at_risk_customers = sum(s.count for s in segments if s.segment == 'At Risk')
                if at_risk_customers > 0:
                    insights['customer_insights'].append({
                        'type': 'retention',
                        'title': 'Customer Retention Alert',
                        'description': f'{at_risk_customers} customers at risk of churn',
                        'recommendation': 'Implement retention campaigns for at-risk customers'
                    })
            
            # Anomaly detection
            anomalies = PredictiveAnalytics.detect_anomalies(user_id, 'revenue')
            if anomalies:
                insights['risk_alerts'].extend([
                    {
                        'type': 'anomaly',
                        'title': f'Revenue {anomaly["type"].title()}',
                        'description': anomaly['description'],
                        'severity': anomaly['severity'],
                        'recommendation': 'Investigate unusual revenue pattern'
                    }
                    for anomaly in anomalies[-3:]  # Last 3 anomalies
                ])
            
            # Growth opportunities
            if forecast.trend_direction == 'increasing':
                insights['growth_opportunities'].append({
                    'type': 'expansion',
                    'title': 'Growth Momentum',
                    'description': 'Revenue trending upward - consider scaling operations',
                    'recommendation': 'Evaluate capacity and consider expansion'
                })
            
            return insights
            
        except Exception as e:
            try:
                logger.error(f"Error generating business insights: {str(e)}")
            except NameError:
                logging.getLogger(__name__).error(f"Error generating business insights: {str(e)}")
            return {
                'revenue_insights': [],
                'customer_insights': [],
                'product_insights': [],
                'operational_insights': [],
                'growth_opportunities': [],
                'risk_alerts': []
            }
    
    @staticmethod
    def _detect_seasonality(values: List[float]) -> bool:
        """Simple seasonality detection using autocorrelation."""
        if len(values) < 12:
            return False
        
        # Check for yearly patterns (12-month lag)
        try:
            correlation = np.corrcoef(values[:-12], values[12:])[0, 1]
            return abs(correlation) > 0.5
        except:
            return False
    
    @staticmethod
    def _generate_revenue_recommendations(predictions: List[float], trend: str, accuracy: float) -> List[str]:
        """Generate revenue-specific recommendations."""
        recommendations = []
        
        if accuracy < 0.6:
            recommendations.append("Forecast accuracy is low - gather more historical data")
        
        if trend == 'increasing':
            recommendations.append("Revenue trending up - consider scaling operations")
            recommendations.append("Invest in marketing to maintain growth momentum")
        elif trend == 'decreasing':
            recommendations.append("Revenue declining - investigate causes and implement recovery plan")
            recommendations.append("Consider promotional activities to boost sales")
        else:
            recommendations.append("Revenue stable - focus on optimization and efficiency")
        
        if len(predictions) > 0 and predictions[-1] > predictions[0] * 1.2:
            recommendations.append("Strong growth predicted - ensure operational readiness")
        
        return recommendations
    
    @staticmethod
    def _generate_segment_recommendations(segment: str, count: int) -> List[str]:
        """Generate segment-specific recommendations."""
        recommendations = []
        
        if segment == 'Champions':
            recommendations.extend([
                "Provide VIP treatment and exclusive offers",
                "Ask for referrals and testimonials",
                "Involve in product development feedback"
            ])
        elif segment == 'Loyal Customers':
            recommendations.extend([
                "Maintain regular communication",
                "Offer loyalty rewards and early access",
                "Cross-sell complementary products"
            ])
        elif segment == 'At Risk':
            recommendations.extend([
                "Send re-engagement campaigns",
                "Offer special discounts or incentives",
                "Understand reasons for reduced engagement"
            ])
        elif segment == 'Lost':
            recommendations.extend([
                "Send win-back campaigns with strong offers",
                "Survey to understand reasons for leaving",
                "Focus on acquiring new customers"
            ])
        else:  # New
            recommendations.extend([
                "Provide excellent onboarding experience",
                "Educate about product benefits",
                "Build relationship through regular contact"
            ])
        
        return recommendations
    
    @staticmethod
    def _create_insufficient_data_forecast() -> ForecastResult:
        """Create forecast when insufficient data is available."""
        return ForecastResult(
            predictions=[0.0] * 12,
            confidence_intervals=[(0.0, 0.0)] * 12,
            accuracy_score=0.0,
            trend_direction='unknown',
            seasonality_detected=False,
            recommendations=['Insufficient historical data for accurate forecasting']
        )
    
    @staticmethod
    def _create_error_forecast() -> ForecastResult:
        """Create forecast when error occurs."""
        return ForecastResult(
            predictions=[],
            confidence_intervals=[],
            accuracy_score=0.0,
            trend_direction='unknown',
            seasonality_detected=False,
            recommendations=['Error occurred during forecasting']
        )
