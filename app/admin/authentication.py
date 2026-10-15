import uuid
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from settings.config import AppSettings

class AdminAuthenticationBackend(AuthenticationBackend):
    def __init__(self, settings: AppSettings):
        # Инициализируем базовый класс секретным ключом 
        super().__init__(secret_key=settings.ADMIN_SECRET_KEY.get_secret_value())
        self._admin_login = settings.ADMIN_LOGIN.get_secret_value()
        self._admin_password = settings.ADMIN_PASSWORD.get_secret_value()
        self._admin_session_token = None

    async def login(self, request: Request) -> bool:
        """Метод авторизации администратора по форме в браузере (Шаг 3 пункта 8 ТЗ)"""
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        # Проверяем совпадение логина и пароля с конфигами
        if username == self._admin_login and password == self._admin_password:
            # Генерируем уникальный токен сессии
            self._admin_session_token = str(uuid.uuid4())
            # Записываем токен в сессию пользователя
            request.session.update({"token": self._admin_session_token})
            return True
            
        return False

    async def authenticate(self, request: Request) -> bool:
        """Проверка наличия токена при каждом переходе по вкладкам админки (Шаг 3 пункта 9 ТЗ)"""
        token = request.session.get("token")
        
        if not token or token != self._admin_session_token:
            return False
            
        return True

    async def logout(self, request: Request) -> bool:
        """Очистка сессии при нажатии кнопки Выйти (Шаг 3 пункта 10 ТЗ)"""
        request.session.clear()
        return True
