from sqlalchemy import Column, Integer, String, Float, DateTime
from database.database import Base
from datetime import datetime

class CompanyScore(Base):
    __tablename__ = "company_scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_code = Column(String(50), unique=True, index=True)
    physical_capacity_score = Column(Float, default=0.0)
    financial_support_score = Column(Float, default=0.0)
    strategic_intent_score = Column(Float, default=0.0)
    local_limitation_score = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
