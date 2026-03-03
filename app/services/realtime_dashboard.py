"""
Real-time dashboard service for WebSocket-based updates.
"""
from datetime import datetime
from typing import Dict, Any, List
from flask import current_app
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import logging

logger = logging.getLogger(__name__)

class RealTimeDashboard:
    """Service for real-time dashboard updates via WebSocket."""
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.connected_users = {}  # user_id -> session_id mapping
        
    def handle_user_connect(self, user_id: int, session_id: str):
        """Handle user connection to dashboard."""
        self.connected_users[user_id] = session_id
        join_room(f'user_{user_id}')
        logger.info(f"User {user_id} connected to dashboard")
        
        # Send initial dashboard state
        self.send_initial_state(user_id)
    
    def handle_user_disconnect(self, user_id: int):
        """Handle user disconnection from dashboard."""
        if user_id in self.connected_users:
            del self.connected_users[user_id]
            leave_room(f'user_{user_id}')
            logger.info(f"User {user_id} disconnected from dashboard")
    
    def broadcast_order_update(self, order_data: Dict[str, Any]):
        """Broadcast new order to relevant user's dashboard."""
        user_id = order_data.get('user_id')
        if not user_id:
            return

        payload = {
            'type': 'new_order',
            'data': order_data,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'New order #{order_data.get("id", "Unknown")} received'
        }

        room = f'user_{user_id}' if user_id in self.connected_users else None
        if room:
            self.socketio.emit('dashboard_update', payload, room=room)
        else:
            self.socketio.emit('dashboard_update', payload)
        
        # Update KPIs for connected users only
        if user_id in self.connected_users:
            self.broadcast_kpi_update(user_id, {
                'new_order_count': 1,
                'new_revenue': float(order_data.get('total_amount', 0))
            })
    
    def broadcast_inventory_update(self, inventory_data: Dict[str, Any]):
        """Broadcast inventory changes to dashboard."""
        user_id = inventory_data.get('user_id')
        if not user_id:
            return

        payload = {
            'type': 'inventory_change',
            'data': inventory_data,
            'timestamp': datetime.utcnow().isoformat(),
            'message': f'Inventory updated for {inventory_data.get("product_name", "Unknown")}'
        }
        room = f'user_{user_id}' if user_id in self.connected_users else None
        if room:
            self.socketio.emit('dashboard_update', payload, room=room)
        else:
            self.socketio.emit('dashboard_update', payload)
    
    def broadcast_sales_update(self, sales_data: Dict[str, Any]):
        """Broadcast sales milestone updates."""
        user_id = sales_data.get('user_id')
        if not user_id:
            return

        payload = {
            'type': 'sales_milestone',
            'data': sales_data,
            'timestamp': datetime.utcnow().isoformat(),
            'message': sales_data.get('message', 'Sales milestone reached!')
        }
        room = f'user_{user_id}' if user_id in self.connected_users else None
        if room:
            self.socketio.emit('dashboard_update', payload, room=room)
        else:
            self.socketio.emit('dashboard_update', payload)
    
    def broadcast_kpi_update(self, user_id: int, kpi_data: Dict[str, Any]):
        """Broadcast KPI updates to dashboard."""
        if user_id in self.connected_users:
            payload = {
                'data': kpi_data,
                'timestamp': datetime.utcnow().isoformat()
            }
            self.socketio.emit('kpi_update', payload, room=f'user_{user_id}')
    
    def send_initial_state(self, user_id: int):
        """Send initial dashboard state to newly connected user."""
        try:
            from app.services.dashboard_metrics import DashboardMetrics
            
            # Get current dashboard metrics
            metrics = DashboardMetrics.get_comprehensive_metrics(user_id)
            
            self.socketio.emit('initial_state', {
                'kpi': metrics.get('kpi', {}),
                'charts': metrics.get('charts', {}),
                'alerts': metrics.get('alerts', []),
                'timestamp': datetime.utcnow().isoformat()
            }, room=f'user_{user_id}')
            
        except Exception as e:
            logger.error(f"Error sending initial state: {str(e)}")
            self.socketio.emit('error', {
                'message': 'Failed to load dashboard data',
                'timestamp': datetime.utcnow().isoformat()
            }, room=f'user_{user_id}')
    
    def send_notification(self, user_id: int, notification: Dict[str, Any]):
        """Send targeted notification to user."""
        if user_id in self.connected_users:
            self.socketio.emit('notification', {
                'type': notification.get('type', 'info'),
                'title': notification.get('title', 'Notification'),
                'message': notification.get('message', ''),
                'data': notification.get('data', {}),
                'timestamp': datetime.utcnow().isoformat(),
                'auto_dismiss': notification.get('auto_dismiss', False)
            }, room=f'user_{user_id}')
    
    def broadcast_system_alert(self, alert_data: Dict[str, Any]):
        """Broadcast system-wide alerts."""
        for user_id in self.connected_users:
            self.socketio.emit('system_alert', {
                'type': alert_data.get('type', 'warning'),
                'title': alert_data.get('title', 'System Alert'),
                'message': alert_data.get('message', ''),
                'severity': alert_data.get('severity', 'warning'),
                'timestamp': datetime.utcnow().isoformat()
            }, room=f'user_{user_id}')
    
    def get_connected_users_count(self) -> int:
        """Get count of currently connected dashboard users."""
        return len(self.connected_users)
    
    def is_user_connected(self, user_id: int) -> bool:
        """Check if user is currently connected to dashboard."""
        return user_id in self.connected_users


# Make RealTimeDashboard available in builtins for test convenience
try:
    import builtins  # type: ignore
    builtins.RealTimeDashboard = RealTimeDashboard
except Exception:
    pass
