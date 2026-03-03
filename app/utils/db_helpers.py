"""
Database helpers used across the app for session hygiene.
"""
from flask import current_app, g, has_app_context
from sqlalchemy.exc import SQLAlchemyError

from app import db


def rollback_db_session():
    """Rollback the current session but keep it bound so the request can continue."""
    try:
        db.session.rollback()
    except (SQLAlchemyError, RuntimeError) as exc:
        if has_app_context():
            current_app.logger.debug("Failed to rollback db.session: %s", exc)
    finally:
        try:
            db.session.expire_all()
        except (SQLAlchemyError, RuntimeError) as exc:
            if has_app_context():
                current_app.logger.debug("Failed to expire db.session after rollback: %s", exc)


def reset_db_session():
    """Fully reset the scoped session when a clean slate is required."""
    rollback_db_session()
    try:
        db.session.remove()
    except (SQLAlchemyError, RuntimeError) as exc:
        if has_app_context():
            current_app.logger.debug("Failed to remove db.session: %s", exc)
    finally:
        if has_app_context():
            g.pop("_login_user", None)
