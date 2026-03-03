from __future__ import annotations
from enum import Enum, auto
from datetime import datetime
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Import db directly to avoid circular imports
from app.models import db, BaseModelMixin

if TYPE_CHECKING:
    from app.models.users import User
    from app.models.products import Product

class CostTypeEnum(str, Enum):
    """Enum for different types of costs with classification metadata."""
    
    # Variable Costs (directly tied to production volume)
    RAW_MATERIALS = 'raw_materials'
    DIRECT_LABOR = 'labor'
    SHIPPING = 'shipping'
    PACKAGING = 'packaging'
    
    # Fixed Costs (incurred regardless of production volume)
    RENT = 'rent'
    UTILITIES = 'utilities'
    SALARIES = 'salaries'
    INSURANCE = 'insurance'
    SOFTWARE = 'software'
    PROFESSIONAL_FEES = 'professional_fees'
    
    # Semi-variable Costs (have both fixed and variable components)
    MAINTENANCE = 'maintenance'
    MARKETING = 'marketing'
    
    # Other
    OTHER = 'other'

class CostType(db.Model):
    """SQLAlchemy model for cost types."""
    __tablename__ = 'cost_types'
    
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    def __init__(self, id, name):
        # Validate that the id is a valid CostTypeEnum value
        if id not in [t.value for t in CostTypeEnum]:
            raise ValueError(f"Invalid cost type: {id}")
        self.id = id
        self.name = name
    
    def __repr__(self):
        return f'<CostType {self.id}: {self.name}>'


class CostClassification(str, Enum):
    """Classification of costs based on their behavior."""
    FIXED = 'FIXED'
    VARIABLE = 'VARIABLE'
    SEMI_VARIABLE = 'SEMI_VARIABLE'
    
    @classmethod
    def from_cost_type(cls, cost_type: CostTypeEnum) -> 'CostClassification':
        """Get the default classification for a cost type."""
        if cost_type in {
            CostTypeEnum.RAW_MATERIALS,
            CostTypeEnum.DIRECT_LABOR,
            CostTypeEnum.SHIPPING,
            CostTypeEnum.PACKAGING
        }:
            return cls.VARIABLE
        elif cost_type in {
            CostTypeEnum.RENT,
            CostTypeEnum.UTILITIES,
            CostTypeEnum.SALARIES
        }:
            return cls.FIXED
        return cls.SEMI_VARIABLE


class CostEntry(db.Model, BaseModelMixin):
    """
    Represents a cost entry in the system with enhanced type safety and relationships.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        product_id: Optional foreign key to Product if cost is product-specific
        date: Date when the cost was incurred
        amount: Monetary amount of the cost
        cost_type: Type of cost (from CostTypeEnum)
        classification: Whether the cost is fixed, variable, or semi-variable
        is_direct: Whether this is a direct cost (directly attributable to a product)
        is_tax_deductible: Whether this cost is tax deductible
        description: Optional description of the cost
        is_recurring: Whether this is a recurring cost
        recurrence_frequency: Frequency of recurrence (monthly, quarterly, yearly)
        created_at: When the record was created
        updated_at: When the record was last updated
    """
    __tablename__ = 'cost_entries'
    __table_args__ = (
        db.Index('idx_cost_entry_user_date', 'user_id', 'date'),
        db.Index('idx_cost_entry_classification', 'user_id', 'classification'),
    )
    
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id: Mapped[Optional[int]] = mapped_column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    date: Mapped[datetime.date] = mapped_column(db.Date, nullable=False, default=datetime.utcnow)
    amount: Mapped[Decimal] = mapped_column(db.Numeric(10, 2), nullable=False)
    cost_type: Mapped[CostTypeEnum] = mapped_column(db.Enum(CostTypeEnum), nullable=False)
    classification: Mapped[CostClassification] = mapped_column(
        db.Enum(CostClassification), 
        nullable=False,
        default=CostClassification.FIXED
    )
    is_direct: Mapped[bool] = mapped_column(db.Boolean, default=False)
    is_tax_deductible: Mapped[bool] = mapped_column(db.Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(db.String(200))
    is_recurring: Mapped[bool] = mapped_column(db.Boolean, default=False)
    recurrence_frequency: Mapped[Optional[str]] = mapped_column(db.String(20))
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        db.DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
    
    # Relationships
    user: Mapped['User'] = relationship('User', back_populates='cost_entries')
    product: Mapped[Optional['Product']] = relationship('Product', back_populates='cost_entries')
    
    def __init__(self, **kwargs: Any) -> None:
        # Set default classification based on cost_type if not provided
        if 'cost_type' in kwargs and 'classification' not in kwargs:
            cost_type = kwargs['cost_type']
            if isinstance(cost_type, str):
                cost_type = CostTypeEnum(cost_type)
            kwargs['classification'] = CostClassification.from_cost_type(cost_type)
        super().__init__(**kwargs)
    
    def __repr__(self) -> str:
        return f"<CostEntry(id={self.id}, amount={self.amount}, type={self.cost_type}, date={self.date})>"
    
    @property
    def is_variable_cost(self) -> bool:
        """Check if this is a variable cost."""
        return self.classification == CostClassification.VARIABLE
    
    @property
    def is_fixed_cost(self) -> bool:
        """Check if this is a fixed cost."""
        return self.classification == CostClassification.FIXED
    
    @classmethod
    def get_cost_breakdown(
        cls, 
        user_id: int, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get breakdown of costs by classification and category.
        
        Args:
            user_id: ID of the user
            start_date: Start date of the period
            end_date: End date of the period
            
        Returns:
            Dictionary containing cost breakdown with the following keys:
            - fixed_costs: Total fixed costs
            - variable_costs: Total variable costs
            - semi_variable_costs: Total semi-variable costs
            - by_category: Dictionary of costs by category
        """
        from sqlalchemy import func, case
        
        # Get total costs by classification
        result = db.session.query(
            cls.classification,
            func.sum(cls.amount).label('total_amount')
        ).filter(
            cls.user_id == user_id,
            cls.date.between(start_date, end_date)
        ).group_by(cls.classification).all()
        
        # Initialize result dictionary
        breakdown = {
            'fixed_costs': 0,
            'variable_costs': 0,
            'semi_variable_costs': 0,
            'by_category': {}
        }
        
        # Process classification totals
        for classification, amount in result:
            if classification == CostClassification.FIXED:
                breakdown['fixed_costs'] = float(amount)
            elif classification == CostClassification.VARIABLE:
                breakdown['variable_costs'] = float(amount)
            elif classification == CostClassification.SEMI_VARIABLE:
                breakdown['semi_variable_costs'] = float(amount)
        
        # Get costs by category
        category_totals = db.session.query(
            cls.cost_type,
            func.sum(cls.amount).label('total_amount')
        ).filter(
            cls.user_id == user_id,
            cls.date.between(start_date, end_date)
        ).group_by(cls.cost_type).all()
        
        # Process category totals
        for cost_type, amount in category_totals:
            breakdown['by_category'][cost_type.value] = float(amount)
        
        return breakdown
    
    @classmethod
    def calculate_contribution_margin(
        cls,
        user_id: int,
        revenue: float,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, float]:
        """
        Calculate contribution margin and related metrics.
        
        Args:
            user_id: ID of the user
            revenue: Total revenue for the period
            start_date: Start of the analysis period
            end_date: End of the analysis period
            
        Returns:
            Dictionary containing:
            - contribution_margin: Revenue minus variable costs
            - contribution_margin_ratio: (Revenue - Variable Costs) / Revenue
            - break_even_point: Fixed Costs / Contribution Margin Ratio
            - fixed_costs: Total fixed costs
            - variable_costs: Total variable costs
        """
        # Get cost breakdown
        costs = cls.get_cost_breakdown(user_id, start_date, end_date)
        
        fixed_costs = costs['fixed_costs']
        variable_costs = costs['variable_costs']
        
        # Calculate metrics
        contribution_margin = revenue - variable_costs
        contribution_margin_ratio = (contribution_margin / revenue) if revenue > 0 else 0
        break_even_point = fixed_costs / contribution_margin_ratio if contribution_margin_ratio > 0 else 0
        
        return {
            'contribution_margin': contribution_margin,
            'contribution_margin_ratio': contribution_margin_ratio,
            'break_even_point': break_even_point,
            'fixed_costs': fixed_costs,
            'variable_costs': variable_costs
        }
