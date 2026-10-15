import asyncio
import json
from vk_api.utils import get_random_id
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from app.models import Base, User
from app.core.users.constants import RolesEnum
from app.core.orders.models import Order, OrderedProduct
from app.core.orders.constants import OrderStatusEnum
from app.core.orders.exceptions import ActiveOrderExists
from app.handlers.helpers import build_order_buttons, format_order_content, format_order_contents_for_waiter

class BotHandler:
    def __init__(self, command_text: str, handler_func, role: RolesEnum = None):
        self.command_text = command_text
        self.handler_func = handler_func
        self.role = role

def get_keyboard_by_role(role: RolesEnum):
    """Генерирует надежную клавиатуру без смайликов, которую ВК откроет на 100%"""
    keyboard = VkKeyboard(one_time=False)
    if role == RolesEnum.waiter:
        keyboard.add_button("заказы в работе", color=VkKeyboardColor.PRIMARY)
    else:
        keyboard.add_button("сделать заказ", color=VkKeyboardColor.POSITIVE)
    return keyboard.get_keyboard()

def get_keyboard_by_role_raw(role_str: str):
    """Вспомогательная функция для main.py"""
    role = RolesEnum.waiter if role_str == "waiter" else RolesEnum.customer
    return get_keyboard_by_role(role)

async def customer_start_handler(vk, user_id: int, services) -> None:
    """Приветствие обычного посетителя"""
    repo = services["user_repo"]
    await repo.create_user_if_not_exists(user_id=user_id)
    await asyncio.to_thread(
        vk.messages.send, user_id=user_id, 
        message="Добро пожаловать в наше кафе-мороженое! Используйте кнопку меню ниже:", 
        keyboard=get_keyboard_by_role(RolesEnum.customer), random_id=get_random_id()
    )

async def waiter_start_handler(vk, user_id: int, services) -> None:
    """Приветствие официанта с гарантированным выводом кнопок"""
    await asyncio.to_thread(
        vk.messages.send, user_id=user_id, 
        message="С возвращением на смену! Панель управления активна.", 
        keyboard=get_keyboard_by_role(RolesEnum.waiter), 
        random_id=get_random_id()
    )

async def change_role_dev_handler(vk, user_id: int, new_role_str: str, app_instance) -> None:
    """Хэндлер быстрой смены ролей с жестким обновлением кэша памяти приложения"""
    target_role = RolesEnum.waiter if "официант" in new_role_str else RolesEnum.customer

    async with app_instance.database.session() as session:
        stmt = update(User).where(User.vk_id == user_id).values(role=target_role)
        await session.execute(stmt)
            
    if target_role == RolesEnum.waiter:
        app_instance._roles[RolesEnum.waiter].add(user_id)
    else:
        app_instance._roles[RolesEnum.waiter].discard(user_id)

    await asyncio.to_thread(
        vk.messages.send, user_id=user_id, 
        message=f"Роль успешно изменена на: {target_role.value}!", 
        keyboard=get_keyboard_by_role(target_role), random_id=get_random_id()
    )

async def create_order_handler(vk, user_id: int, services) -> None:
    """Точка входа в заказ (Шаг 2)"""
    order_service = services["order_service"]
    product_service = services["product_service"]
    
    try:
        order_id = await order_service.create_order(user_id=user_id)
        products = await product_service.list_products()
        await asyncio.to_thread(
            vk.messages.send, user_id=user_id,
            message="🛒 Добавьте блюдо или напиток в заказ:\n(В вашей корзине пока пусто)",
            keyboard=build_order_buttons(order_id, products), random_id=get_random_id()
        )
    except ActiveOrderExists:
        active_order = await order_service.get_active_order_for_user(user_id)
        products = await product_service.list_products()
        cart_text = format_order_content(active_order)
        
        if active_order.status == OrderStatusEnum.ordered:
            message = f"У вас уже есть активный заказ №{active_order.id}, ожидайте сборки официантом!\n\n{cart_text}"
            await asyncio.to_thread(vk.messages.send, user_id=user_id, message=message, random_id=get_random_id())
        else:
            message = f"У вас остался незавершенный черновик заказа №{active_order.id}.\nВы можете продолжить выбор:"
            await asyncio.to_thread(vk.messages.send, user_id=user_id, message=message, keyboard=build_order_buttons(active_order.id, products), random_id=get_random_id())

async def add_item_handler(vk, user_id: int, payload_data: dict, services) -> None:
    """Добавление выбранной позиции в корзину (Шаг 3)"""
    order_service = services["order_service"]
    product_service = services["product_service"]
    
    order_id = payload_data["order_id"]
    product_id = payload_data["product_id"]
    
    await order_service.add_product_to_order(order_id, product_id)
    updated_order = await order_service.get_order_by_id(order_id)
    products = await product_service.list_products()
    
    await asyncio.to_thread(
        vk.messages.send, user_id=user_id,
        message=format_order_content(updated_order),
        keyboard=build_order_buttons(order_id, products), random_id=get_random_id()
    )

async def finish_order_handler(vk, user_id: int, payload_data: dict, services) -> None:
    """Передача готового заказа официантам (Шаг 4)"""
    order_service = services["order_service"]
    user_repo = services["user_repo"]
    order_id = payload_data["order_id"]
    
    await order_service.send_order_to_waiters(order_id)
    order = await order_service.get_order_by_id(order_id)
    
    await asyncio.to_thread(
        vk.messages.send, user_id=user_id,
        message="Заказ был передан нашим официантам, ожидайте в ближайшее время!",
        keyboard=get_keyboard_by_role(RolesEnum.customer), random_id=get_random_id()
    )
    
    waiter_ids = await user_repo.get_waiter_user_ids()
    waiter_msg = format_order_contents_for_waiter(order)
    
    for waiter_id in waiter_ids:
        waiter_kb = VkKeyboard(inline=True)
        waiter_payload = {"action": "waiter_finish", "order_id": order_id}
        waiter_kb.add_button(f"Заказ {order_id} выдан", color=VkKeyboardColor.POSITIVE, payload=json.dumps(waiter_payload))
        try:
            await asyncio.to_thread(vk.messages.send, user_id=waiter_id, message=waiter_msg, keyboard=waiter_kb.get_keyboard(), random_id=get_random_id())
        except Exception:
            pass

async def display_pending_orders_handler(vk, user_id: int, services) -> None:
    """Хэндлер отображения активных заказов для роли официанта"""
    order_service = services["order_service"]
    
    async with order_service.repository.database.session() as session:
        query = select(Order).where(Order.status == OrderStatusEnum.ordered).order_by(Order.id).options(
            joinedload(Order.products).joinedload(OrderedProduct.product)
        )
        result = await session.execute(query)
        pending_orders = result.scalars().unique().all()

    if not pending_orders:
        await asyncio.to_thread(
            vk.messages.send, user_id=user_id, 
            message="Нет активных заказов в очереди. Все клиенты довольны!", 
            keyboard=get_keyboard_by_role(RolesEnum.waiter), random_id=get_random_id()
        )
        return

    lines = []
    inline_keyboard = VkKeyboard(inline=True)
    for index, order in enumerate(pending_orders):
        order_text = f"Заказ №{order.id} (Клиент: ://vk.com{order.user_id})\n"
        for op in order.products:
            order_text += f"• {op.product.name} — {op.amount} шт.\n"
        lines.append(order_text)
        
        inline_keyboard.add_button(f"Выдать {order.id}", color=VkKeyboardColor.POSITIVE, payload=json.dumps({"action": "waiter_finish", "order_id": order.id}))
        if (index + 1) % 2 == 0 and index < len(pending_orders) - 1:
            inline_keyboard.add_line()
            
    message = "Список активных заказов в работе:\n\n" + "\n\n".join(lines) + "\nКликните по кнопке ниже, чтобы выдать заказ:"
    await asyncio.to_thread(vk.messages.send, user_id=user_id, message=message, keyboard=inline_keyboard.get_keyboard(), random_id=get_random_id())

async def waiter_finish_order_handler(vk, waiter_id: int, payload_data: dict, services) -> None:
    """Официант закрывает заказ (Шаг 5)"""
    order_service = services["order_service"]
    order_id = payload_data["order_id"]
    
    order = await order_service.get_order_by_id(order_id)
    if order and order.status != OrderStatusEnum.done:
        await order_service.mark_order_done(order_id)
        await asyncio.to_thread(vk.messages.send, user_id=waiter_id, message=f"Заказ №{order_id} успешно переведен в статус: ВЫДАН.", random_id=get_random_id())
        try:
            await asyncio.to_thread(vk.messages.send, user_id=order.user_id, message=f"Ваш заказ №{order_id} успешно приготовлен и выдан гостю! Приятного аппетита!", random_id=get_random_id())
        except Exception:
            pass

HANDLERS = [
    BotHandler("регистрация", customer_start_handler, role=RolesEnum.customer),
    BotHandler("старт", customer_start_handler, role=RolesEnum.customer),
    BotHandler("старт", waiter_start_handler, role=RolesEnum.waiter),
    BotHandler("заказы в работе", display_pending_orders_handler, role=RolesEnum.waiter),
]
