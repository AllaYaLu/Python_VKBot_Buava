import asyncio
import logging
import json
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from settings.config import AppSettings

from app.database import Database 
from app.repositories import UserRepository
from app.core.users.constants import RolesEnum


from app.core.orders.repositories import ProductRepository, OrderRepository
from app.core.orders.services import ProductService, OrderService
from app.handlers.commands import HANDLERS, change_role_dev_handler, create_order_handler, add_item_handler, finish_order_handler, display_pending_orders_handler, waiter_finish_order_handler, get_keyboard_by_role_raw


class Application:
    def __init__(self, app_settings: AppSettings) -> None:
        self.settings = app_settings
        token_str = self.settings.VK_API_KEY.get_secret_value()
        self.vk_session = vk_api.VkApi(token=token_str)
        self.vk = self.vk_session.get_api()
        self.longpoll = None
        

        self.database = Database(app_settings=self.settings)
        self.user_repository = UserRepository(database=self.database)
        
      
        self.product_repo = ProductRepository(database=self.database)
        self.product_service = ProductService(repository=self.product_repo)
        
        self.order_repo = OrderRepository(database=self.database)
        self.order_service = OrderService(repository=self.order_repo)
        
      
        self.services = {
            "user_repo": self.user_repository,
            "product_service": self.product_service,
            "order_service": self.order_service
        }
        
        self._roles = {RolesEnum.waiter: set(), RolesEnum.customer: set()}
        logging.info("Бот-Кафе полностью инициализирован на трехслойной архитектуре.")

    async def setup_roles(self) -> None:
        try:
            waiter_ids = await self.user_repository.get_waiter_user_ids()
            self._roles[RolesEnum.waiter] = set(waiter_ids)
            logging.info(f"Список официантов обновлен. Найдено ID: {list(self._roles[RolesEnum.waiter])}")
        except Exception as e:
            logging.error(f"Ошибка при синхронизации ролей: {e}")

    async def setup_jobs(self) -> None:
        while True:
            await asyncio.sleep(60)
            await self.setup_roles()

    async def application_startup(self) -> None:
        await self.database.create_tables()
        await self.setup_roles()
        asyncio.create_task(self.setup_jobs())

    async def application_shutdown(self) -> None:
        await self.database.shutdown()

    async def run(self) -> None:
        await self.application_startup()
        logging.info("Запуск пуллинга сообщений ВК...")
        
        while True:
            try:
                self.longpoll = VkLongPoll(self.vk_session)
                break
            except Exception as e:
                await asyncio.sleep(5)

        while True: 
            events = await asyncio.to_thread(self.longpoll.check)
            if events: 
                for event in events: 
                    if event.type == VkEventType.MESSAGE_NEW and event.to_me: 
                        user_id = event.user_id 
                        user_text = event.text.lower().strip()
                        
                  
                        payload_data = None
                        if hasattr(event, 'extra_values') and event.extra_values.get('payload'):
                            try:
                                payload_data = json.loads(event.extra_values['payload'])
                            except Exception:
                                pass
                                
                        if payload_data and "action" in payload_data:
                            action = payload_data["action"]
                            logging.info(f"Перехвачено инлайн-действие: {action} от пользователя {user_id}")
                            
                            if action == "start_order":
                                await create_order_handler(vk=self.vk, user_id=user_id, services=self.services)
                            elif action == "add_item":
                                await add_item_handler(vk=self.vk, user_id=user_id, payload_data=payload_data, services=self.services)
                            elif action == "finish_order":
                                await finish_order_handler(vk=self.vk, user_id=user_id, payload_data=payload_data, services=self.services)
                            elif action == "waiter_finish":
                                await waiter_finish_order_handler(vk=self.vk, waiter_id=user_id, payload_data=payload_data, services=self.services)
                            continue

                     
                        if user_text in ["стать официантом", "стать клиентом"]:
                       
                            await change_role_dev_handler(vk=self.vk, user_id=user_id, new_role_str=user_text, app_instance=self)
                            continue
                        
                        if user_text == "сделать заказ":
                            await create_order_handler(vk=self.vk, user_id=user_id, services=self.services)
                            continue

                        handler_triggered = False
                        for h in HANDLERS:
                            if h.command_text == user_text:
                                if h.role == RolesEnum.waiter and user_id in self._roles[RolesEnum.waiter]:
                
                                    await h.handler_func(vk=self.vk, user_id=user_id, services=self.services)
                                    handler_triggered = True
                                    break
                                elif h.role == RolesEnum.customer and user_id not in self._roles[RolesEnum.waiter]:
                      
                                    await h.handler_func(vk=self.vk, user_id=user_id, services=self.services)
                                    handler_triggered = True
                                    break

                        if not handler_triggered:
                            current_role = RolesEnum.waiter if user_id in self._roles[RolesEnum.waiter] else RolesEnum.customer
                            await asyncio.to_thread(
                                self.vk.messages.send, user_id=user_id, 
                                message="Привет! Я бот кафе-мороженого. Используйте меню ниже:", 
                                keyboard=get_keyboard_by_role_raw(current_role), random_id=0
                            )
            
            await asyncio.sleep(0.05)
