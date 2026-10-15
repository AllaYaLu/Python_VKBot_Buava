from decimal import Decimal
from sqlalchemy import BIGINT, INTEGER, ForeignKey, TEXT, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models import Base

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    name: Mapped[str] = mapped_column(TEXT, unique=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.vk_id"), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="unlisted", nullable=False)

    products: Mapped[list["OrderedProduct"]] = relationship()

class OrderedProduct(Base):
    __tablename__ = "orders_products"

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    amount: Mapped[int] = mapped_column(INTEGER, nullable=False)

    product: Mapped[Product] = relationship()
