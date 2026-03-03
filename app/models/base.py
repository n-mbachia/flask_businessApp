"""
Base model for all database models.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy
db = SQLAlchemy()

class BaseModelMixin:
    """Base model mixin with common fields and methods."""
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, 
                         onupdate=datetime.utcnow, nullable=False)

    def save(self):
        """Save the current model to the database."""
        db.session.add(self)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def delete(self):
        """Delete the current model from the database."""
        db.session.delete(self)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
            
    def update(self, **kwargs):
        """Update model attributes."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self.save()
