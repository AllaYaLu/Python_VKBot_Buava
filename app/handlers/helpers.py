import json
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from app.core.orders.models import Order, Product
from app.core.orders.constants import OrderStatusEnum

def build_order_buttons(order_id: int, items: list[Product]):
    """
    Генерирует инлайн-клавиатуру меню для ВК (Шаг 2 пункт 3).
    В payload передаем JSON-структуру, аналогично кортежам из Telegram!
    """
    keyboard = VkKeyboard(inline=True)
    
    for index, item in enumerate(items):
        # Передаем словарь: действие, id_заказа, id_продукта
        payload = {"action": "add_item", "order_id": order_id, "product_id": item.id}
        keyboard.add_button(item.name, color=VkKeyboardColor.PRIMARY, payload=json.dumps(payload))
        
        # Разделяем кнопки на ряды, если позиций много (максимум 4 в ряд)
        if (index + 1) % 2 == 0 and index < len(items) - 1:
            keyboard.add_line()
            
    # Добавляем финальную кнопку завершения сборки корзины
    if len(items) > 0:
        keyboard.add_line()
        
    finish_payload = {"action": "finish_order", "order_id": order_id}
    keyboard.add_button("Завершить заказ", color=VkKeyboardColor.POSITIVE, payload=json.dumps(finish_payload))
    
    return keyboard.get_keyboard()

def format_order_content(order: Order) -> str:
    """Форматирует отображение корзины для посетителя"""
    if not order.products:
        return "🛒 В вашей корзине пока пусто.\nВыберите, что хотите заказать из меню выше:"
        
    msg_text = "🛒 **Текущий состав вашей корзины:**\n\n"
    for op in order.products:
        msg_text += f"• {op.product.name} — {op.amount} шт.\n"
        
    if order.status == OrderStatusEnum.unlisted:
        # 🌟 Добавили вопрос-подсказку для пользователя, как ты просила!
        msg_text += "\n🤔 Желаете добавить что-нибудь ещё из меню выше? Или нажмите «Завершить заказ» для отправки на кухню."
    return msg_text


def format_order_contents_for_waiter(order: Order) -> str:
    """Форматирует текст состава заказа для отправки в чат официантам"""
    msg_text = f"🔔 **Новый заказ №{order.id}!**\n👤 Посетитель: ://vk.com{order.user_id}\n\n**Состав заказа:**\n"
    for op in order.products:
        msg_text += f"• {op.product.name} — {op.amount} шт.\n"
    return msg_text

