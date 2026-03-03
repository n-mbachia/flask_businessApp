"""
Predictive Analytics API endpoints.
"""
from flask_restx import Namespace, Resource, fields
import flask_login
from flask import request
from datetime import datetime
from typing import Dict, Any

# Import predictive analytics service
from app.services.predictive_analytics import PredictiveAnalytics

# Create namespace
ns = Namespace('predictive', description='Predictive analytics operations')

# Response models
forecast_model = ns.model('Forecast', {
    'predictions': fields.List(fields.Float, description='Predicted values'),
    'confidence_intervals': fields.List(fields.List(fields.Float), description='Confidence intervals'),
    'accuracy_score': fields.Float(description='Forecast accuracy score'),
    'trend_direction': fields.String(description='Trend direction (increasing/decreasing/stable)'),
    'seasonality_detected': fields.Boolean(description='Whether seasonality was detected'),
    'recommendations': fields.List(fields.String, description='Business recommendations')
})

customer_segment_model = ns.model('CustomerSegment', {
    'segment': fields.String(description='Segment name'),
    'count': fields.Integer(description='Number of customers in segment'),
    'avg_lifetime_value': fields.Float(description='Average customer lifetime value'),
    'avg_order_frequency': fields.Float(description='Average order frequency'),
    'churn_risk': fields.Float(description='Churn risk percentage'),
    'recommendations': fields.List(fields.String, description='Segment-specific recommendations')
})

insight_model = ns.model('Insight', {
    'type': fields.String(description='Insight type'),
    'title': fields.String(description='Insight title'),
    'description': fields.String(description='Insight description'),
    'recommendation': fields.String(description='Recommended action'),
    'severity': fields.String(description='Severity level (if applicable)')
})

anomaly_model = ns.model('Anomaly', {
    'date': fields.String(description='Date of anomaly'),
    'metric': fields.String(description='Metric with anomaly'),
    'value': fields.Float(description='Actual value'),
    'expected': fields.Float(description='Expected value'),
    'z_score': fields.Float(description='Statistical z-score'),
    'severity': fields.String(description='Anomaly severity'),
    'type': fields.String(description='Anomaly type (spike/drop)'),
    'description': fields.String(description='Anomaly description')
})

business_intelligence_model = ns.model('BusinessIntelligence', {
    'revenue_insights': fields.List(fields.Nested(insight_model)),
    'customer_insights': fields.List(fields.Nested(insight_model)),
    'product_insights': fields.List(fields.Nested(insight_model)),
    'operational_insights': fields.List(fields.Nested(insight_model)),
    'growth_opportunities': fields.List(fields.Nested(insight_model)),
    'risk_alerts': fields.List(fields.Nested(insight_model))
})

error_model = ns.model('Error', {
    'error': fields.String(description='Error message'),
    'details': fields.String(description='Error details')
})

@ns.route('/revenue/forecast')
class RevenueForecast(Resource):
    @ns.doc('get_revenue_forecast')
    def get(self):
        """Generate revenue forecast with confidence intervals."""
        try:
            if not flask_login.current_user or not getattr(flask_login.current_user, 'is_authenticated', False):
                return {'error': 'Unauthorized'}, 401
            # Parse query parameters
            periods = request.args.get('periods', 12, type=int)
            confidence_level = request.args.get('confidence', 0.95, type=float)
            
            # Validate parameters
            if periods < 1 or periods > 24:
                return {
                    'error': 'Invalid periods parameter. Must be between 1 and 24',
                    'details': 'Requested forecast periods exceed maximum allowed'
                }, 400
            
            if confidence_level not in [0.8, 0.9, 0.95]:
                confidence_level = 0.95
            
            # Generate forecast
            forecast = PredictiveAnalytics.forecast_revenue(
                user_id=flask_login.current_user.id,
                periods=periods,
                confidence_level=confidence_level
            )
            
            return {
                'success': True,
                'data': {
                    'predictions': forecast.predictions,
                    'confidence_intervals': forecast.confidence_intervals,
                    'accuracy_score': forecast.accuracy_score,
                    'trend_direction': forecast.trend_direction,
                    'seasonality_detected': forecast.seasonality_detected,
                    'recommendations': forecast.recommendations
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': 'Failed to generate revenue forecast',
                'details': str(e)
            }, 500

@ns.route('/customers/segments')
class CustomerSegments(Resource):
    @ns.doc('get_customer_segments')
    def get(self):
        """Get RFM customer segmentation analysis."""
        try:
            if not flask_login.current_user or not getattr(flask_login.current_user, 'is_authenticated', False):
                return {'error': 'Unauthorized'}, 401

            segments = PredictiveAnalytics.customer_segmentation(flask_login.current_user.id)
            
            return {
                'success': True,
                'data': [
                    {
                        'segment': segment.segment,
                        'count': segment.count,
                        'avg_lifetime_value': segment.avg_lifetime_value,
                        'avg_order_frequency': segment.avg_order_frequency,
                        'churn_risk': segment.churn_risk,
                        'recommendations': segment.recommendations
                    }
                    for segment in segments
                ]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': 'Failed to generate customer segments',
                'details': str(e)
            }, 500

@ns.route('/anomalies')
class AnomalyDetection(Resource):
    @ns.doc('detect_anomalies')
    def get(self):
        """Detect statistical anomalies in business metrics."""
        try:
            if not flask_login.current_user or not getattr(flask_login.current_user, 'is_authenticated', False):
                return {'error': 'Unauthorized'}, 401
            # Parse query parameters
            metric = request.args.get('metric', 'revenue')
            threshold = request.args.get('threshold', 2.0, type=float)
            
            # Validate parameters
            valid_metrics = ['revenue', 'orders', 'customers']
            if metric not in valid_metrics:
                return {
                    'error': 'Invalid metric parameter',
                    'details': f'Must be one of: {", ".join(valid_metrics)}'
                }, 400
            
            if threshold < 1.0 or threshold > 5.0:
                return {
                    'error': 'Invalid threshold parameter',
                    'details': 'Must be between 1.0 and 5.0 standard deviations'
                }, 400
            
            # Detect anomalies
            anomalies = PredictiveAnalytics.detect_anomalies(
                user_id=flask_login.current_user.id,
                metric=metric,
                threshold=threshold
            )
            
            return {
                'success': True,
                'data': anomalies,
                'count': len(anomalies)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': 'Failed to detect anomalies',
                'details': str(e)
            }, 500

@ns.route('/insights')
class BusinessIntelligence(Resource):
    @ns.doc('get_business_insights')
    def get(self):
        """Generate comprehensive business insights and recommendations."""
        try:
            if not flask_login.current_user or not getattr(flask_login.current_user, 'is_authenticated', False):
                return {'error': 'Unauthorized'}, 401

            insights = PredictiveAnalytics.generate_business_insights(flask_login.current_user.id)
            
            return {
                'success': True,
                'data': insights,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': 'Failed to generate business insights',
                'details': str(e)
            }, 500

@ns.route('/dashboard/predictive')
class PredictiveDashboard(Resource):
    @ns.doc('get_predictive_dashboard')
    def get(self):
        """Get all predictive analytics data for dashboard."""
        try:
            if not flask_login.current_user or not getattr(flask_login.current_user, 'is_authenticated', False):
                return {'error': 'Unauthorized'}, 401
            # Get all predictive data in parallel
            forecast = PredictiveAnalytics.forecast_revenue(flask_login.current_user.id, periods=6)
            segments = PredictiveAnalytics.customer_segmentation(flask_login.current_user.id)
            anomalies = PredictiveAnalytics.detect_anomalies(flask_login.current_user.id, 'revenue')
            insights = PredictiveAnalytics.generate_business_insights(flask_login.current_user.id)
            
            return {
                'success': True,
                'data': {
                    'forecast': {
                        'predictions': forecast.predictions[:6],  # Next 6 months
                        'accuracy_score': forecast.accuracy_score,
                        'trend_direction': forecast.trend_direction,
                        'recommendations': forecast.recommendations[:3]  # Top 3 recommendations
                    },
                    'segments': [
                        {
                            'segment': segment.segment,
                            'count': segment.count,
                            'churn_risk': segment.churn_risk,
                            'recommendations': segment.recommendations[:2]  # Top 2 recommendations
                        }
                        for segment in segments
                    ],
                    'anomalies': anomalies[-3:],  # Last 3 anomalies
                    'insights': {
                        'revenue_insights': insights.get('revenue_insights', [])[:2],
                        'customer_insights': insights.get('customer_insights', [])[:2],
                        'growth_opportunities': insights.get('growth_opportunities', [])[:2],
                        'risk_alerts': insights.get('risk_alerts', [])[:2]
                    }
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': 'Failed to load predictive dashboard data',
                'details': str(e)
            }, 500
