# F:\МебельПрайсПро\my_app\models.py

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.sql import func
# from sqlalchemy.dialects.postgresql import JSONB # Если используете PostgreSQL для JSON полей
# from sqlalchemy import JSON # Универсальный тип JSON, если поддерживается вашей СУБД

db = SQLAlchemy()

# Статусы Техкарты
TECH_CARD_STATUS_DRAFT = "Черновик"
TECH_CARD_STATUS_PENDING_ACCOUNTANT = "На согласовании (Бухгалтер)"
TECH_CARD_STATUS_REJECTED_ACCOUNTANT = "Отклонена (Бухгалтер)"
TECH_CARD_STATUS_PENDING_MANAGER = "На согласовании (Руководитель)"
TECH_CARD_STATUS_REJECTED_MANAGER = "Отклонена (Руководитель)"
TECH_CARD_STATUS_APPROVED = "Утверждена"
TECH_CARD_STATUS_ARCHIVED = "Архивная"
TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES = "Обработана (требует цен)" # После парсинга, если не все цены сырья найдены
TECH_CARD_STATUS_PROCESSED = "Обработана" # После парсинга, все цены найдены

# Роли пользователей
USER_ROLE_ADMIN = "admin"
USER_ROLE_EDITOR = "editor" # Редактор техкарт
USER_ROLE_ACCOUNTANT = "accountant" # Производственный бухгалтер
USER_ROLE_SALES_MANAGER = "sales_manager" # Руководитель отдела продаж
USER_ROLE_CEO = "ceo" # Генеральный директор
USER_ROLE_CLIENT = "client" # Обычный клиент сайта

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    registration_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    role = db.Column(db.String(50), nullable=False, default=USER_ROLE_CLIENT)
    # is_admin поле можно оставить для супер-администратора или удалить в пользу ролей
    is_admin = db.Column(db.Boolean, nullable=False, default=False) 
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_login = db.Column(db.DateTime, nullable=True)

    addresses = db.relationship('Address', backref='user', lazy=True, cascade="all, delete-orphan")
    orders = db.relationship('Order', backref='user', lazy=True) 
    cart = db.relationship('Cart', backref='user', uselist=False, lazy=True, cascade="all, delete-orphan") 
    wishlist = db.relationship('Wishlist', backref='user', uselist=False, lazy=True, cascade="all, delete-orphan") 
    
    tech_cards_created = db.relationship('TechCard', foreign_keys='TechCard.created_by_id', backref='creator', lazy='dynamic')
    tech_cards_approved_accountant = db.relationship('TechCard', foreign_keys='TechCard.accountant_approver_id', backref='accountant_approver', lazy='dynamic')
    tech_cards_approved_manager = db.relationship('TechCard', foreign_keys='TechCard.manager_approver_id', backref='manager_approver', lazy='dynamic')
    
    created_approval_tasks = db.relationship('ApprovalTask', foreign_keys='ApprovalTask.created_by_id', backref='task_creator_user', lazy='dynamic')
    assigned_approval_tasks = db.relationship('ApprovalTask', foreign_keys='ApprovalTask.assigned_to_id', backref='assignee_user', lazy='dynamic')

    def has_role(self, role_name):
        return self.role == role_name

    def __repr__(self):
        return f'<User {self.username} (Role: {self.role})>'

class TechCard(db.Model):
    __tablename__ = 'tech_cards'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False) 
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False) 
    version = db.Column(db.String(50), nullable=True, default='1.0')
    description = db.Column(db.Text, nullable=True) # Комментарий редактора при создании/отправке
    
    status = db.Column(db.String(50), default=TECH_CARD_STATUS_DRAFT, nullable=False) 
    
    total_cost = db.Column(db.Numeric(12, 2), nullable=True) # Рассчитанная себестоимость по этой техкарте

    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) 
    
    # Информация о согласовании Бухгалтером
    accountant_approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    accountant_approval_timestamp = db.Column(db.DateTime, nullable=True)
    accountant_rejection_reason = db.Column(db.Text, nullable=True)

    # Информация о согласовании Руководителем
    manager_approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    manager_approval_timestamp = db.Column(db.DateTime, nullable=True)
    manager_rejection_reason = db.Column(db.Text, nullable=True)
    
    file_url = db.Column(db.String(255), nullable=True) 
    parsed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    components = db.relationship('TechCardComponent', backref='tech_card_details', lazy='dynamic', cascade="all, delete-orphan")
    product_owner = db.relationship('Product', backref=db.backref('owned_tech_cards', lazy='dynamic')) # Изменил backref, чтобы не конфликтовать с product.tech_cards

    def __repr__(self):
        return f'<TechCard ID {self.id} for Product ID {self.product_id} - v{self.version} ({self.status})>'

# --- Остальные модели (Product, ProductImage, RawMaterial, TechCardComponent, и т.д.) ---
# Убедитесь, что они здесь присутствуют, как в артефакте sqlalchemy_models_final.
# Я их здесь не дублирую для краткости, но они должны быть в вашем файле.
# ВАЖНО: В модели Product свойство active_tech_card теперь должно искать техкарту со статусом TECH_CARD_STATUS_APPROVED.

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True) 
    short_description = db.Column(db.Text, nullable=True)
    sku = db.Column(db.String(100), unique=True, nullable=False) 
    
    cost_price = db.Column(db.Numeric(10, 2), nullable=True) 
    cost_price_source = db.Column(db.String(100), nullable=True) 
    
    price = db.Column(db.Numeric(10, 2), nullable=True) 
    markup_percentage = db.Column(db.Numeric(5, 2), nullable=True) 
    discounted_price = db.Column(db.Numeric(10, 2), nullable=True) 

    wholesale_price = db.Column(db.Numeric(10, 2), nullable=True) 
    wholesale_markup_percentage = db.Column(db.Numeric(5, 2), nullable=True) 
    
    dealer_price = db.Column(db.Numeric(10, 2), nullable=True) 
    dealer_markup_percentage = db.Column(db.Numeric(5, 2), nullable=True) 

    availability_status = db.Column(db.String(50), nullable=False, default='in_stock') 
    stock_quantity = db.Column(db.Integer, nullable=True, default=0) 

    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=True) 
    
    weight = db.Column(db.Numeric(8, 2), nullable=True) 
    dimensions = db.Column(db.String(100), nullable=True) 
    
    specifications = db.Column(db.Text, nullable=True) 

    dealer_id = db.Column(db.Integer, db.ForeignKey('dealers.id'), nullable=True) 

    seo_title = db.Column(db.String(255), nullable=True)
    seo_description = db.Column(db.Text, nullable=True)
    seo_keywords = db.Column(db.String(255), nullable=True) 

    images = db.relationship('ProductImage', backref='product', lazy='dynamic', cascade="all, delete-orphan", order_by="ProductImage.order_index")
    # tech_cards уже определена через backref 'product_owner' в TechCard

    @property
    def active_approved_tech_card(self): # Ищем последнюю УТВЕРЖДЕННУЮ техкарту
        return TechCard.query.filter_by(product_id=self.id, status=TECH_CARD_STATUS_APPROVED).order_by(TechCard.updated_at.desc()).first()
        
    def __repr__(self):
        return f'<Product {self.name} (SKU: {self.sku})>'


class ProductImage(db.Model): __tablename__ = 'product_images'; id = db.Column(db.Integer, primary_key=True); product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False); image_url = db.Column(db.String(255), nullable=False) ; alt_text = db.Column(db.String(200), nullable=True); order_index = db.Column(db.Integer, default=0, nullable=False); is_main = db.Column(db.Boolean, default=False)
class RawMaterial(db.Model): __tablename__ = 'raw_materials'; id = db.Column(db.Integer, primary_key=True); sku = db.Column(db.String(100), unique=True, nullable=True) ; name = db.Column(db.String(150), nullable=False, index=True, unique=True); description = db.Column(db.Text, nullable=True); unit_of_measurement = db.Column(db.String(20), nullable=False); price = db.Column(db.Numeric(10, 2), nullable=True, default=0.00) ; updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow); tech_card_components = db.relationship('TechCardComponent', backref='raw_material_item', lazy='dynamic')
class TechCardComponent(db.Model): __tablename__ = 'tech_card_components'; id = db.Column(db.Integer, primary_key=True); tech_card_id = db.Column(db.Integer, db.ForeignKey('tech_cards.id'), nullable=False); raw_material_id = db.Column(db.Integer, db.ForeignKey('raw_materials.id'), nullable=False); quantity = db.Column(db.Numeric(10, 3), nullable=False) ; notes = db.Column(db.Text, nullable=True)
class Category(db.Model): __tablename__ = 'categories'; id = db.Column(db.Integer, primary_key=True); name = db.Column(db.String(100), unique=True, nullable=False); slug = db.Column(db.String(120), unique=True, nullable=False); description = db.Column(db.Text, nullable=True); parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True); image_url = db.Column(db.String(255), nullable=True); products = db.relationship('Product', backref='category', lazy='dynamic'); parent = db.relationship('Category', remote_side=[id], backref='subcategories', lazy=True)
class Address(db.Model): __tablename__ = 'addresses'; id = db.Column(db.Integer, primary_key=True); user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False); city = db.Column(db.String(100), nullable=False); street = db.Column(db.String(200), nullable=False); house_number = db.Column(db.String(20), nullable=False); apartment_number = db.Column(db.String(20), nullable=True); postal_code = db.Column(db.String(20), nullable=True); is_default = db.Column(db.Boolean, default=False)
class Cart(db.Model): __tablename__ = 'carts'; id = db.Column(db.Integer, primary_key=True); user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, unique=True); session_id = db.Column(db.String(255), nullable=True, unique=True); created_at = db.Column(db.DateTime, default=datetime.utcnow); updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow); items = db.relationship('CartItem', backref='cart', lazy='dynamic', cascade="all, delete-orphan")
class CartItem(db.Model): __tablename__ = 'cart_items'; id = db.Column(db.Integer, primary_key=True); cart_id = db.Column(db.Integer, db.ForeignKey('carts.id'), nullable=False); product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False); quantity = db.Column(db.Integer, nullable=False, default=1); added_at = db.Column(db.DateTime, default=datetime.utcnow); product = db.relationship('Product', lazy=True)
class Order(db.Model): __tablename__ = 'orders'; id = db.Column(db.Integer, primary_key=True); user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True); customer_name = db.Column(db.String(100), nullable=True); customer_email = db.Column(db.String(120), nullable=True); customer_phone = db.Column(db.String(20), nullable=True); shipping_address_text = db.Column(db.Text, nullable=True); billing_address_text = db.Column(db.Text, nullable=True); total_amount = db.Column(db.Numeric(12, 2), nullable=False); status = db.Column(db.String(50), nullable=False, default='Новый'); payment_method = db.Column(db.String(50), nullable=True); payment_status = db.Column(db.String(50), nullable=True, default='Ожидает оплаты'); created_at = db.Column(db.DateTime, default=datetime.utcnow); updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow); shipping_cost = db.Column(db.Numeric(10, 2), nullable=True, default=0.00); tracking_number = db.Column(db.String(100), nullable=True); items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade="all, delete-orphan")
class OrderItem(db.Model): __tablename__ = 'order_items'; id = db.Column(db.Integer, primary_key=True); order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False); product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False); quantity = db.Column(db.Integer, nullable=False); price_at_purchase = db.Column(db.Numeric(10, 2), nullable=False); product = db.relationship('Product', lazy=True)
class Dealer(db.Model): __tablename__ = 'dealers'; id = db.Column(db.Integer, primary_key=True); name = db.Column(db.String(150), nullable=False, unique=True); contact_person = db.Column(db.String(100), nullable=True); email = db.Column(db.String(120), nullable=True, unique=True); phone = db.Column(db.String(50), nullable=True); address = db.Column(db.Text, nullable=True); products_supplied = db.relationship('Product', backref='supplying_dealer', lazy='dynamic') # Изменил backref на supplying_dealer
class ApprovalTask(db.Model): __tablename__ = 'approval_tasks'; id = db.Column(db.Integer, primary_key=True); entity_type = db.Column(db.String(50), nullable=False); entity_id = db.Column(db.Integer, nullable=False); status = db.Column(db.String(50), default='Ожидает'); created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False); assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True); comments = db.Column(db.Text, nullable=True); created_at = db.Column(db.DateTime, default=datetime.utcnow); resolved_at = db.Column(db.DateTime, nullable=True)
class Wishlist(db.Model): __tablename__ = 'wishlists'; id = db.Column(db.Integer, primary_key=True); user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False); items = db.relationship('WishlistItem', backref='wishlist', lazy='dynamic', cascade="all, delete-orphan")
class WishlistItem(db.Model): __tablename__ = 'wishlist_items'; id = db.Column(db.Integer, primary_key=True); wishlist_id = db.Column(db.Integer, db.ForeignKey('wishlists.id'), nullable=False); product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False); added_at = db.Column(db.DateTime, default=datetime.utcnow); product = db.relationship('Product', lazy=True)

