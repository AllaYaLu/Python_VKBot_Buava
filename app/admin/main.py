import uvicorn
from starlette.applications import Starlette
from sqladmin import Admin

from app.admin.authentication import AdminAuthenticationBackend
from app.admin.views import UserAdmin, ProductAdmin, OrderAdmin
from app.database import Database
from settings.config import AppSettings

class AdminApplication:
    def __init__(self, app_settings: AppSettings) -> None:
        # 1. Создаем экземпляр Starlette 
        self.web_app = Starlette()
        
        # 2. Используем наш класс базы данных
        self.database = Database(app_settings=app_settings)
        
        # 3. Настраиваем авторизацию и панель управления Admin
        auth_backend = AdminAuthenticationBackend(settings=app_settings)
        self.admin = Admin(
            app=self.web_app,
            engine=self.database.engine,  # Передаем движок СУБД из нашего класса
            authentication_backend=auth_backend,
            base_url="/"
        )
        
        # 4. Регистрируем представления таблиц
        self._register_views()

    def _register_views(self) -> None:
        """Регистрация отображения таблиц в веб-панели"""  
        self.admin.add_view(UserAdmin)
        self.admin.add_view(ProductAdmin)  
        self.admin.add_view(OrderAdmin)    


def create_app() -> Starlette:
    """Фабрика для сборки приложения под веб-сервер uvicorn (Пункт 6 ТЗ)"""
    settings = AppSettings()
    admin_app = AdminApplication(app_settings=settings)
    return admin_app.web_app

# Секция запуска локального uvicorn-сервера панели 
if __name__ == "__main__":
    settings = AppSettings()
    uvicorn.run(
        "app.admin.main:create_app", 
        factory=True,
        host="127.0.0.1",
        port=settings.ADMIN_INTERFACE_PORT,
        log_level="info",
        workers=1
    )
