"""
WebSocket event handlers for real-time dashboard functionality.
"""
from datetime import datetime
from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
from app.services.realtime_dashboard import RealTimeDashboard
import logging

logger = logging.getLogger(__name__)

# Global instance will be initialized in app.py
realtime_service = None

def init_realtime_dashboard(socketio):
    """Initialize real-time dashboard service."""
    global realtime_service
    realtime_service = RealTimeDashboard(socketio)
    return realtime_service

def handle_connect():
    """Handle client connection."""
    if current_user.is_authenticated:
        user_id = current_user.id
        session_id = request.sid  # Flask-SocketIO provides this
        
        realtime_service.handle_user_connect(user_id, session_id)
        
        emit('connected', {
            'message': 'Connected to real-time dashboard',
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info(f"Client connected: {user_id}")
    else:
        emit('error', {'message': 'Authentication required'})
        return False

def handle_disconnect():
    """Handle client disconnection."""
    if current_user.is_authenticated:
        user_id = current_user.id
        realtime_service.handle_user_disconnect(user_id)
        logger.info(f"Client disconnected: {user_id}")

def handle_join_dashboard(data):
    """Handle joining dashboard room."""
    if current_user.is_authenticated:
        user_id = current_user.id
        room = data.get('room', f'dashboard_{user_id}')
        join_room(room)
        
        emit('joined_room', {
            'room': room,
            'message': f'Joined {room}'
        })

def handle_leave_dashboard(data):
    """Handle leaving dashboard room."""
    if current_user.is_authenticated:
        room = data.get('room')
        leave_room(room)
        
        emit('left_room', {
            'room': room,
            'message': f'Left {room}'
        })

def handle_request_refresh(data):
    """Handle manual refresh request."""
    if current_user.is_authenticated:
        user_id = current_user.id
        realtime_service.send_initial_state(user_id)
        
        emit('refresh_complete', {
            'message': 'Dashboard refreshed',
            'timestamp': datetime.utcnow().isoformat()
        })

def handle_subscribe_metrics(data):
    """Handle subscription to specific metrics updates."""
    if current_user.is_authenticated:
        user_id = current_user.id
        metrics = data.get('metrics', [])
        
        # Join metric-specific rooms
        for metric in metrics:
            join_room(f'metric_{metric}_{user_id}')
        
        emit('subscribed', {
            'metrics': metrics,
            'message': f'Subscribed to {len(metrics)} metrics'
        })

def handle_unsubscribe_metrics(data):
    """Handle unsubscription from specific metrics updates."""
    if current_user.is_authenticated:
        user_id = current_user.id
        metrics = data.get('metrics', [])
        
        # Leave metric-specific rooms
        for metric in metrics:
            leave_room(f'metric_{metric}_{user_id}')
        
        emit('unsubscribed', {
            'metrics': metrics,
            'message': f'Unsubscribed from {len(metrics)} metrics'
        })

# Event registration function
def register_socketio_events(socketio):
    """Register all WebSocket event handlers."""
    
    @socketio.on('connect')
    def on_connect():
        return handle_connect()
    
    @socketio.on('disconnect')
    def on_disconnect():
        return handle_disconnect()
    
    @socketio.on('join_dashboard')
    def on_join_dashboard(data):
        return handle_join_dashboard(data)
    
    @socketio.on('leave_dashboard')
    def on_leave_dashboard(data):
        return handle_leave_dashboard(data)
    
    @socketio.on('request_refresh')
    def on_request_refresh(data):
        return handle_request_refresh(data)
    
    @socketio.on('subscribe_metrics')
    def on_subscribe_metrics(data):
        return handle_subscribe_metrics(data)
    
    @socketio.on('unsubscribe_metrics')
    def on_unsubscribe_metrics(data):
        return handle_unsubscribe_metrics(data)
    
    logger.info("WebSocket event handlers registered")
