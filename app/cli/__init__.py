# app/cli/__init__.py
"""
CLI commands package.
"""
from .admin_commands import register_admin_commands
from .utility_commands import register_utility_commands

def register_all_commands(app):
    """Register all CLI commands."""
    register_admin_commands(app)
    register_utility_commands(app)
