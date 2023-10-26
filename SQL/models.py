from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
import sqlalchemy as db
from typing import List
from datetime import date, datetime

class Base(DeclarativeBase):
    pass

class Trends(Base):
    __tablename__ = "Tendencias"

    id: Mapped[int] = mapped_column(primary_key=True)
    keywords: Mapped[str] = mapped_column(db.String(256))
    date: Mapped[date] = mapped_column(db.Date)
    category: Mapped[str] = mapped_column(db.String(154))

    def __repr__(self) -> str:
        return f"Trends(id={self.id}, trend={self.keywords}, category={self.category})"
    
class Auth(Base):
    __tablename__ = "Autenticacion"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    access_token: Mapped[str] = mapped_column(db.Text)
    expires_in: Mapped[datetime] = mapped_column(db.DateTime)
    refresh_token: Mapped[str] = mapped_column(db.String(42))
    
class Category(Base):
    __tablename__ = "Categorias"
    
    id: Mapped[str] = mapped_column(db.String(9), primary_key=True)
    name: Mapped[str] = mapped_column(db.String(152))
    
    def __repr__(self) -> str:
        return f"Category(id={self.id}, name={self.name})"
    
class TrendingItems(Base):
    __tablename__ = "ProductosYTendencias"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[str] = mapped_column(db.String(15))
    name: Mapped[str] = mapped_column(db.String(80))
    seller_id: Mapped[str] = mapped_column(db.String(12))
    price: Mapped[int] = mapped_column(db.Integer)
    keyword: Mapped[str] = mapped_column(db.String(256))
    items_sold: Mapped[int] = mapped_column(db.Integer)
    publication_date: Mapped[date] = mapped_column(db.Date)
    visits: Mapped[int] = mapped_column(db.Integer)
    quality: Mapped[float] = mapped_column(db.Float)
    category: Mapped[str] = mapped_column(db.String(152))

    def __repr__(self) -> str:
        return f"Item(id={self.item_id}, name={self.name})"


class Reviews(Base):
    __tablename__ = "Opiniones"

    id: Mapped[str] = mapped_column(db.String(9), primary_key=True)
    item_id: Mapped[str] = mapped_column(db.String(15))
    rate: Mapped[int] = mapped_column(db.Integer)
    content: Mapped[str] = mapped_column(db.UnicodeText)

    def __repr__(self) -> str:
        return f"Review(id={self.id}, rate={self.rate})"