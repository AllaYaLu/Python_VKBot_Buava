from dataclasses import dataclass
from sqlalchemy import select, update, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.dialects.postgresql import insert
from app.database import Database
from app.core.orders.models import Product, Order, OrderedProduct
from app.core.orders.constants import OrderStatusEnum

@dataclass
class ProductRepository:
    database: Database

    async def list_products(self) -> list[Product]:
        """Получить список всех товаров в меню кафе"""
        async with self.database.session() as session:
            query = select(Product)
            result = await session.scalars(query)
            return list(result.all())

@dataclass
class OrderRepository:
    database: Database

    async def create_order(self, user_id: int) -> int:
        """Создать новый пустой черновик заказа"""
        async with self.database.session() as session:
            insert_stmt = insert(Order).values(user_id=user_id, status=OrderStatusEnum.unlisted)
            order_id = await session.execute(insert_stmt)
            return order_id.scalar()

    async def get_order_by_id(self, order_id: int) -> Order | None:
        """Получить заказ по ID вместе со всеми выбранными продуктами"""
        async with self.database.session() as session:
            query = select(Order).where(Order.id == order_id).options(
                joinedload(Order.products).joinedload(OrderedProduct.product)
            )
            return await session.scalar(query)

    async def get_active_order_for_user(self, user_id: int) -> Order | None:
        """Найти текущий активный заказ (unlisted или ordered) для пользователя"""
        async with self.database.session() as session:
            query = select(Order).where(
                and_(
                    Order.user_id == user_id,
                    Order.status.in_([OrderStatusEnum.unlisted, OrderStatusEnum.ordered])
                )
            ).options(
                joinedload(Order.products).joinedload(OrderedProduct.product)
            )
            return await session.scalar(query)

    async def add_product_to_order(self, order_id: int, product_id: int) -> None:
        """Добавить продукт в заказ или увеличить его количество на 1 (UPSERT)"""
        async with self.database.session() as session:
            insert_stmt = insert(OrderedProduct).values(
                order_id=order_id, product_id=product_id, amount=1
            )
            # Если запись уже есть, увеличиваем счетчик количества
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[OrderedProduct.order_id, OrderedProduct.product_id],
                set_={"amount": OrderedProduct.amount + 1}
            )
            await session.execute(upsert_stmt)

    async def set_order_status(self, order_id: int, status: OrderStatusEnum) -> None:
        """Обновить статус заказа в базе данных"""
        async with self.database.session() as session:
            stmt = update(Order).where(Order.id == order_id).values(status=status)
            await session.execute(stmt)
