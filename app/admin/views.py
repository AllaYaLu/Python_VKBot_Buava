from sqladmin import ModelView
from app.models import User
from app.core.orders.models import Product, Order

class UserAdmin(ModelView, model=User):
    column_list = [User.vk_id, User.username, User.role]
    form_include_pk = True

class ProductAdmin(ModelView, model=Product):
    column_list = [Product.id, Product.name, Product.price]
    form_include_pk = True

class OrderAdmin(ModelView, model=Order):
    column_list = [Order.id, Order.user_id, Order.status]

    form_include_pk = True
