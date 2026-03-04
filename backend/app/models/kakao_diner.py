from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, ULIDMixin


class KakaoDiner(Base, ULIDMixin):
    __tablename__ = "kakao_diner"

    diner_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    tag = Column(Text)
    menu_name = Column(Text)
    menu_price = Column(Text)
    review_cnt = Column(Integer)
    review_avg = Column(Float)
    blog_review_cnt = Column(Float)
    review_tags = Column(Text)
    road_address = Column(Text)
    num_address = Column(Text)
    phone = Column(String(50))
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    open_time = Column(Text)
    category_large = Column(String(100))
    category_middle = Column(String(100))
    category_small = Column(String(100))
    category_detail = Column(String(100))
    grade = Column(Integer)
    hidden_score = Column(Float)
    bayesian_score = Column(Float)
    crawled_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    reviews = relationship("KakaoReview", back_populates="diner")
    mappings = relationship("ItemKakaoMapping", back_populates="diner")
    open_hours = relationship("KakaoDinerOpenHours", back_populates="diner")
    menus = relationship("KakaoDinerMenu", back_populates="diner")
    ai_data = relationship("KakaoDinerAIData", back_populates="diner", uselist=False)
