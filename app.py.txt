# F:\МебельПрайсПро\app.py

import os
import json 
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation 
from functools import wraps
import logging

from flask import (Flask, render_template, request, redirect, url_for, flash, 
                   jsonify, current_app, session) 
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash 
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, func 

# --- Инициализация Flask приложения ---
app = Flask(__name__)

# --- Конфигурация приложения ---
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'your_VERY_VERY_secret_and_random_key_here_CHANGE_ME_ASAP_AGAIN_AND_AGAIN_FINAL_V2_LOGIN_ROUTES_HTML_INTEGRATED_DASH') 
basedir = os.path.abspath(os.path.dirname(__file__))

# Настройка логирования Flask
if not app.debug:
    app.logger.setLevel(logging.INFO)
else:
    app.logger.setLevel(logging.DEBUG)

app.logger.info("Приложение Flask запускается...")

instance_path = os.path.join(basedir, 'instance')
os.makedirs(instance_path, exist_ok=True) 
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + os.path.join(instance_path, 'mebelprice_main_v11.db') # Обновил имя БД
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False 

UPLOAD_FOLDER_STATIC_BASE = os.path.join(basedir, 'static', 'uploads') 
UPLOAD_FOLDER_PRODUCT_IMAGES = os.path.join(UPLOAD_FOLDER_STATIC_BASE, 'product_images')
UPLOAD_FOLDER_TECH_CARDS_EXCEL = os.path.join(basedir, 'uploads_private', 'tech_cards_excel') 

app.config['UPLOAD_FOLDER_PRODUCT_IMAGES'] = UPLOAD_FOLDER_PRODUCT_IMAGES
app.config['UPLOAD_FOLDER_TECH_CARDS_EXCEL'] = UPLOAD_FOLDER_TECH_CARDS_EXCEL
app.config['ALLOWED_EXTENSIONS_IMAGES'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['ALLOWED_EXTENSIONS_EXCEL'] = {'xlsx', 'xls'}
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER_PRODUCT_IMAGES'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_TECH_CARDS_EXCEL'], exist_ok=True)

try:
    from my_app.models import (db, User, Product, Category, ProductImage, TechCard, 
                               RawMaterial, TechCardComponent, Order, OrderItem, Address, 
                               Cart, CartItem, Dealer, ApprovalTask, Wishlist, WishlistItem,
                               TECH_CARD_STATUS_DRAFT, TECH_CARD_STATUS_PENDING_ACCOUNTANT,
                               TECH_CARD_STATUS_REJECTED_ACCOUNTANT, TECH_CARD_STATUS_PENDING_MANAGER,
                               TECH_CARD_STATUS_REJECTED_MANAGER, TECH_CARD_STATUS_APPROVED,
                               TECH_CARD_STATUS_ARCHIVED, TECH_CARD_STATUS_PROCESSED,
                               TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES,
                               USER_ROLE_ADMIN, USER_ROLE_EDITOR, USER_ROLE_ACCOUNTANT, 
                               USER_ROLE_SALES_MANAGER, USER_ROLE_CEO, USER_ROLE_CLIENT) 
    db.init_app(app) 
    app.logger.info("SQLAlchemy и модели успешно инициализированы из my_app.models.")
except ImportError as e:
    app.logger.critical(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось импортировать модели или константы из my_app.models: {e}", exc_info=True)
    exit()

try:
    from my_app.xlsx_parser import parse_excel_data, DEFAULT_TECH_CARD_VERSION
    app.logger.info("Парсер Excel (xlsx_parser.py) успешно импортирован из my_app.")
except ImportError:
    app.logger.warning("Не удалось импортировать xlsx_parser из my_app. Попытка импорта из текущей директории...")
    try:
        from xlsx_parser import parse_excel_data, DEFAULT_TECH_CARD_VERSION
        app.logger.info("Парсер Excel (xlsx_parser.py) успешно импортирован из текущей директории.")
    except ImportError:
        DEFAULT_TECH_CARD_VERSION = "0.0-stub" 
        def parse_excel_data(filepath, product_sku_hint=None, tech_card_name_hint=None, tech_card_version_hint=None):
            flash("ВНИМАНИЕ: Файл xlsx_parser.py не найден. Используется заглушка для парсинга техкарт!", "danger")
            current_app.logger.warning(f"ЗАГЛУШКА parse_excel_data вызвана для файла: {filepath}")
            return {
                'product_sku': product_sku_hint or "SKU_STUB_PARSER",
                'tech_card_name': tech_card_name_hint or f"Техкарта-Заглушка для {product_sku_hint or 'неизв.'}",
                'tech_card_version': tech_card_version_hint or DEFAULT_TECH_CARD_VERSION,
                'components': [
                     {'num': 1, 'Артикул': "MOCK-ART-01", 'Наименование материала': "Мок-Материал 1", 'Количество': Decimal('2.0'), 'Единица измерения': "шт"},
                     {'num': 2, 'Артикул': "MOCK-ART-02", 'Наименование материала': "Мок-Материал 2", 'Количество': Decimal('5.0'), 'Единица измерения': "м"},
                ],
                'errors': ["Парсер не найден, используется заглушка."],
                'warnings': []
            }
        app.logger.error("КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ: xlsx_parser.py не найден ни в my_app, ни в корне. Используется функция-заглушка.")

@app.template_filter('fromjson')
def fromjson_filter(value):
    if value is None: return {} 
    try: return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        current_app.logger.warning(f"Не удалось декодировать JSON в фильтре: '{value}'")
        return {} 

def allowed_file(filename, config_key_for_extensions): 
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config[config_key_for_extensions]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Пожалуйста, войдите в систему для доступа к этой странице.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Пожалуйста, войдите в систему.", "warning")
            return redirect(url_for('login', next=request.url))
        user = User.query.get(session['user_id'])
        if not user or not user.has_role(USER_ROLE_ADMIN):
            flash("Доступ запрещен. У вас нет прав администратора.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

@app.context_processor
def inject_current_user():
    # Передаем также количество задач на согласование для отображения в сайдбаре
    pending_approvals_count = 0
    if get_current_user(): # Только если пользователь залогинен, чтобы избежать ошибок до входа
        pending_approvals_count = ApprovalTask.query.filter(
            or_(
                ApprovalTask.status == TECH_CARD_STATUS_PENDING_ACCOUNTANT,
                ApprovalTask.status == TECH_CARD_STATUS_PENDING_MANAGER,
                ApprovalTask.status == 'Ожидает' 
            )
        ).count()
    return dict(current_user=get_current_user(), 
                  now=datetime.now, 
                  pending_approvals_count=pending_approvals_count)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if get_current_user():
        user = get_current_user()
        if user.has_role(USER_ROLE_ADMIN):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('index'))

    if request.method == 'POST':
        username_or_email = request.form.get('username')
        password = request.form.get('password')

        if not username_or_email or not password:
            flash('Необходимо указать имя пользователя/email и пароль.', 'danger')
            return render_template('admin/admin_login_page.html', username=username_or_email)

        user = User.query.filter(
            or_(User.username == username_or_email, User.email == username_or_email)
        ).first()
        
        if user and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('Ваш аккаунт неактивен. Обратитесь к администратору.', 'danger')
                return render_template('admin/admin_login_page.html', username=username_or_email)

            session['user_id'] = user.id
            session['user_role'] = user.role 
            user.last_login = datetime.now(timezone.utc)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Ошибка обновления last_login для пользователя {user.id}: {e}")

            flash('Вы успешно вошли в систему!', 'success')
            app.logger.info(f"Пользователь '{user.username}' (ID: {user.id}, Роль: {user.role}) успешно вошел в систему.")
            
            next_url = request.args.get('next')
            if next_url:
                return redirect(next_url)
            
            if user.has_role(USER_ROLE_ADMIN):
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя/email или пароль.', 'danger')
            app.logger.warning(f"Неудачная попытка входа для пользователя: {username_or_email}")

    return render_template('admin/admin_login_page.html') 

@app.route('/logout')
@login_required
def logout():
    user_id = session.pop('user_id', None)
    session.pop('user_role', None)
    if user_id:
        app.logger.info(f"Пользователь ID {user_id} вышел из системы.")
    flash('Вы успешно вышли из системы.', 'info')
    return redirect(url_for('login'))

def get_decimal_from_form(form_field_name, default_value=None):
    value_str = request.form.get(form_field_name)
    if value_str is not None and value_str.strip() != "":
        try: return Decimal(value_str.replace(',', '.'))
        except InvalidOperation:
            flash(f"Некорректное числовое значение для поля '{form_field_name}': '{value_str}'. Использовано значение по умолчанию или 0.", "warning")
            current_app.logger.warning(f"InvalidOperation для поля {form_field_name} со значением {value_str}")
            return default_value if default_value is not None else Decimal('0.00')
    return default_value

def save_product_images_fs(product_id, product_sku):
    saved_image_paths_relative_to_static_uploads = []
    image_files = request.files.getlist('product_images_upload[]') 
    if not image_files: return []

    product_specific_image_folder_name = f"product_{product_id}_{secure_filename(str(product_sku))}"
    product_image_upload_path = os.path.join(current_app.config['UPLOAD_FOLDER_PRODUCT_IMAGES'], product_specific_image_folder_name)
    os.makedirs(product_image_upload_path, exist_ok=True)

    for image_file in image_files:
        if image_file and image_file.filename != '' and allowed_file(image_file.filename, 'ALLOWED_EXTENSIONS_IMAGES'):
            original_filename = secure_filename(image_file.filename)
            filename_prefix = uuid.uuid4().hex[:8]
            unique_filename = f"{filename_prefix}_{original_filename}"
            filepath_on_disk = os.path.join(product_image_upload_path, unique_filename)
            try:
                image_file.save(filepath_on_disk)
                relative_url_path = os.path.join('uploads', 'product_images', product_specific_image_folder_name, unique_filename).replace("\\", "/")
                saved_image_paths_relative_to_static_uploads.append(relative_url_path)
            except Exception as e:
                flash(f"Ошибка при сохранении изображения {original_filename}: {e}", "danger")
                current_app.logger.error(f"Ошибка сохранения файла изображения {original_filename}: {e}", exc_info=True)
    return saved_image_paths_relative_to_static_uploads

def update_product_image_records_db(product, new_image_urls, image_order_json, main_image_filename_from_form, deleted_image_ids_str_list):
    if deleted_image_ids_str_list:
        deleted_ids = [int(id_str) for id_str in deleted_image_ids_str_list if id_str.isdigit()]
        for img_id in deleted_ids:
            img_to_delete = ProductImage.query.get(img_id)
            if img_to_delete and img_to_delete.product_id == product.id:
                try:
                    full_image_path_on_disk = os.path.join(current_app.static_folder, img_to_delete.image_url) 
                    if os.path.exists(full_image_path_on_disk): 
                        os.remove(full_image_path_on_disk)
                except Exception as e: 
                    current_app.logger.error(f"Ошибка при удалении файла изображения с диска {img_to_delete.image_url}: {e}", exc_info=True)
                db.session.delete(img_to_delete)

    for new_url in new_image_urls: 
        db.session.add(ProductImage(product_id=product.id, image_url=new_url))
    
    db.session.flush()

    all_product_images_for_ordering = ProductImage.query.filter_by(product_id=product.id).all()
    image_map_by_filename = {img.image_url.split('/')[-1]: img for img in all_product_images_for_ordering}
    
    ordered_filenames_from_form = []
    if image_order_json:
        try: ordered_filenames_from_form = json.loads(image_order_json)
        except json.JSONDecodeError: 
            flash("Ошибка в данных порядка изображений (некорректный JSON). Порядок не обновлен.", "warning")

    final_ordered_image_objects = []
    for filename in ordered_filenames_from_form:
        if filename in image_map_by_filename:
            final_ordered_image_objects.append(image_map_by_filename.pop(filename))
    final_ordered_image_objects.extend(sorted(image_map_by_filename.values(), key=lambda img: img.id)) 

    for index, img_record in enumerate(final_ordered_image_objects): 
        img_record.order_index = index

    main_image_set = False
    if main_image_filename_from_form:
        for img_record in final_ordered_image_objects: 
            img_record.is_main = (img_record.image_url.endswith(main_image_filename_from_form))
            if img_record.is_main: main_image_set = True
    
    if not main_image_set and final_ordered_image_objects:
        final_ordered_image_objects[0].is_main = True
        main_image_set = True
    
    if main_image_set:
        first_main_found = False
        for img_record in final_ordered_image_objects:
            if img_record.is_main:
                if not first_main_found:
                    first_main_found = True
                else:
                    img_record.is_main = False

def _process_techcard_data_and_update_db(parsed_data, product, tech_card_file_info, 
                                        current_user_id=None, desired_status=TECH_CARD_STATUS_DRAFT, 
                                        editor_comment=None):
    if not parsed_data:
        return None, ["Внутренняя ошибка: нет данных для обработки техкарты."]
    
    old_active_cards = TechCard.query.filter(
        TechCard.product_id == product.id,
        TechCard.status.in_([
            TECH_CARD_STATUS_APPROVED, TECH_CARD_STATUS_PROCESSED, 
            TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES,
            TECH_CARD_STATUS_PENDING_ACCOUNTANT, TECH_CARD_STATUS_PENDING_MANAGER
        ])
    ).all()
    for old_tc in old_active_cards:
        old_tc.status = TECH_CARD_STATUS_ARCHIVED
        db.session.add(old_tc)
    
    tech_card_name = parsed_data.get('tech_card_name', f"Техкарта для {product.name}")
    tech_card_version = parsed_data.get('tech_card_version', datetime.now(timezone.utc).strftime("%Y.%m.%d-%H%M"))
    
    tech_card = TechCard(
        name=tech_card_name,
        product_id=product.id,
        version=tech_card_version,
        file_url=tech_card_file_info['saved_filename_relative_to_uploads_private'],
        status=desired_status, 
        description=editor_comment or parsed_data.get('tech_card_description'),
        parsed_at=datetime.now(timezone.utc),
        created_by_id=current_user_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.session.add(tech_card)
    db.session.flush()

    total_cost_calculated = Decimal('0.0')
    materials_without_price_count = 0
    
    for comp_data in parsed_data.get('components', []):
        mat_sku = comp_data.get('Артикул')
        mat_name = comp_data.get('Наименование материала')
        quantity = comp_data.get('Количество')
        unit = comp_data.get('Единица измерения')
        price_from_excel = comp_data.get('Цена из Excel')

        if not isinstance(quantity, Decimal) or quantity <= Decimal('0'): continue
        if not unit: continue
        if not mat_name and not mat_sku: continue

        raw_material = None
        if mat_sku: raw_material = RawMaterial.query.filter_by(sku=mat_sku).first()
        if not raw_material and mat_name: 
            raw_material = RawMaterial.query.filter(func.lower(RawMaterial.name) == func.lower(mat_name)).first()

        if not raw_material:
            new_mat_name = mat_name or mat_sku
            new_mat_price = price_from_excel if price_from_excel is not None and price_from_excel >= Decimal('0') else Decimal('0.00')
            raw_material = RawMaterial(name=new_mat_name, sku=mat_sku, unit_of_measurement=unit, price=new_mat_price, updated_at=datetime.now(timezone.utc))
            db.session.add(raw_material)
            db.session.flush()
            flash(f"Добавлен новый материал: '{raw_material.name}' (Арт: {raw_material.sku or 'нет'}) с ценой {raw_material.price:.2f} сом.", "info" if raw_material.price > 0 else "warning")
            if raw_material.price <= Decimal('0.00'): materials_without_price_count += 1
        elif mat_sku and not raw_material.sku:
            raw_material.sku = mat_sku
            flash(f"Для материала '{raw_material.name}' обновлен артикул на '{mat_sku}'.", "info")
        
        if raw_material.price is None or raw_material.price <= Decimal('0.00'):
            if price_from_excel is not None and price_from_excel > Decimal('0.00'):
                raw_material.price = price_from_excel
                raw_material.updated_at = datetime.now(timezone.utc)
                flash(f"Для материала '{raw_material.name}' установлена цена из Excel: {price_from_excel:.2f} сом.", "info")
            else:
                materials_without_price_count += 1
                flash(f"Внимание: Материал '{raw_material.name}' (Арт: {raw_material.sku or 'нет'}) имеет нулевую или отсутствующую цену в справочнике.", "warning")
        
        component = TechCardComponent(tech_card_id=tech_card.id, raw_material_id=raw_material.id, quantity=quantity)
        db.session.add(component)
        
        if raw_material.price is not None and raw_material.price > Decimal('0.00'): 
            total_cost_calculated += quantity * raw_material.price
    
    tech_card.total_cost = total_cost_calculated.quantize(Decimal("0.01"))
    
    if materials_without_price_count > 0 and desired_status not in [TECH_CARD_STATUS_DRAFT, TECH_CARD_STATUS_ARCHIVED]:
        tech_card.status = TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES
        flash(f"Техкарта '{tech_card.name}' обработана, но требует уточнения цен для {materials_without_price_count} компонент(ов).", "warning")
    elif desired_status not in [TECH_CARD_STATUS_DRAFT, TECH_CARD_STATUS_ARCHIVED] and tech_card.status != TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES:
        pass

    if tech_card.status in [TECH_CARD_STATUS_APPROVED, TECH_CARD_STATUS_PROCESSED]:
        product.cost_price = tech_card.total_cost
        product.cost_price_source = f"Техкарта v{tech_card.version or '?'} от {tech_card.parsed_at.strftime('%d.%m.%Y %H:%M')} ({tech_card.status})"
        recalculate_all_product_prices(product)
    
    return tech_card, []

def recalculate_all_product_prices(product_obj):
    cost = product_obj.cost_price if product_obj.cost_price is not None else Decimal('0.0')
    
    if product_obj.markup_percentage is not None: 
        product_obj.price = (cost * (Decimal('1') + product_obj.markup_percentage / Decimal('100'))).quantize(Decimal("0.01"))
    elif cost == Decimal('0.0') and product_obj.price is not None: 
        pass 
    else: 
        product_obj.price = cost.quantize(Decimal("0.01"))

    if product_obj.wholesale_markup_percentage is not None: 
        product_obj.wholesale_price = (cost * (Decimal('1') + product_obj.wholesale_markup_percentage / Decimal('100'))).quantize(Decimal("0.01"))
    else: 
        product_obj.wholesale_price = cost.quantize(Decimal("0.01"))

    if product_obj.dealer_markup_percentage is not None: 
        product_obj.dealer_price = (cost * (Decimal('1') + product_obj.dealer_markup_percentage / Decimal('100'))).quantize(Decimal("0.01"))
    else: 
        product_obj.dealer_price = cost.quantize(Decimal("0.01"))

# --- Маршруты Flask ---
@app.route('/admin/product/<int:product_id>/preview-techcard', methods=['POST'])
@admin_required
def admin_preview_techcard_components(product_id):
    product = Product.query.get_or_404(product_id)
    file = request.files.get('tech_card_excel_file_for_preview')

    if not file or file.filename == '': 
        return jsonify(success=False, message="Файл не предоставлен.")
    if not allowed_file(file.filename, 'ALLOWED_EXTENSIONS_EXCEL'): 
        return jsonify(success=False, message="Недопустимый тип файла. Разрешены: .xlsx, .xls")

    temp_filename = secure_filename(f"temp_preview_{uuid.uuid4().hex[:8]}_{file.filename}")
    temp_filepath = os.path.join(current_app.config['UPLOAD_FOLDER_TECH_CARDS_EXCEL'], temp_filename)
    
    try:
        file.save(temp_filepath)
        parsed_data = parse_excel_data(temp_filepath, 
                                       product_sku_hint=product.sku,
                                       tech_card_name_hint=f"Предпросмотр для {product.name}")
    except Exception as e:
        current_app.logger.error(f"Ошибка при временном сохранении файла для предпросмотра: {e}", exc_info=True)
        return jsonify(success=False, message=f"Ошибка сохранения файла для предпросмотра: {str(e)}")
    finally:
        if os.path.exists(temp_filepath): 
            try: os.remove(temp_filepath)
            except Exception as e_rem: current_app.logger.error(f"Ошибка удаления временного файла предпросмотра {temp_filepath}: {e_rem}")

    if not parsed_data:
        return jsonify(success=False, message="Парсер не смог обработать файл (вернул None).")

    parser_errors = parsed_data.get('errors', [])
    parser_warnings = parsed_data.get('warnings', [])

    if parser_errors:
        return jsonify(success=False, message="Ошибки при разборе файла: " + "; ".join(parser_errors), warnings=parser_warnings)

    preview_components_data = []
    total_preview_cost = Decimal('0.0')

    for i, comp_data in enumerate(parsed_data.get('components', [])):
        mat_sku = comp_data.get('Артикул')
        mat_name = comp_data.get('Наименование материала')
        quantity = comp_data.get('Количество')
        unit_from_file = comp_data.get('Единица измерения')
        price_from_excel = comp_data.get('Цена из Excel')

        preview_comp = {
            'num': i + 1,
            'articleFromFile': mat_sku,
            'nameFromFile': mat_name,
            'quantity': float(quantity) if quantity is not None else 0.0,
            'unitFromFile': unit_from_file,
            'rawMaterialId': None,
            'rawMaterialNameDB': mat_name or mat_sku,
            'rawMaterialPriceDB': None,
            'rawMaterialUnitDB': unit_from_file,
            'componentCost': 0.0,
            'foundInDB': False,
            'isNew': True
        }

        raw_material_db = None
        if mat_sku:
            raw_material_db = RawMaterial.query.filter_by(sku=mat_sku).first()
        if not raw_material_db and mat_name:
            raw_material_db = RawMaterial.query.filter(func.lower(RawMaterial.name) == func.lower(mat_name)).first()

        current_component_cost = Decimal('0.0')
        if raw_material_db:
            preview_comp['foundInDB'] = True
            preview_comp['isNew'] = False
            preview_comp['rawMaterialId'] = raw_material_db.id
            preview_comp['rawMaterialNameDB'] = raw_material_db.name
            preview_comp['rawMaterialUnitDB'] = raw_material_db.unit_of_measurement
            
            db_price = raw_material_db.price
            if db_price is not None and db_price > Decimal('0'):
                preview_comp['rawMaterialPriceDB'] = float(db_price)
                current_component_cost = quantity * db_price
            elif price_from_excel is not None and price_from_excel > Decimal('0'):
                preview_comp['rawMaterialPriceDB'] = float(price_from_excel)
                parser_warnings.append(f"Материал '{raw_material_db.name}' имеет цену 0 в БД, но {price_from_excel} в Excel. Будет использована цена из БД для расчета, если она > 0.")
            else: 
                 preview_comp['rawMaterialPriceDB'] = 0.0
                 parser_warnings.append(f"Материал '{raw_material_db.name}' имеет нулевую или отсутствующую цену в справочнике. Себестоимость по нему будет 0.")
        
        elif price_from_excel is not None and price_from_excel > Decimal('0'):
            preview_comp['rawMaterialPriceDB'] = float(price_from_excel)
            parser_warnings.append(f"Новый материал '{mat_name or mat_sku}' будет создан с ценой из Excel: {price_from_excel:.2f}, если не будет найден по имени/артикулу при сохранении.")
        else: 
            preview_comp['rawMaterialPriceDB'] = 0.0
            parser_warnings.append(f"Новый материал '{mat_name or mat_sku}' не найден в БД, цена в Excel отсутствует или 0. Будет создана с ценой 0 (или 1.0) при сохранении.")

        preview_comp['componentCost'] = float(current_component_cost)
        total_preview_cost += current_component_cost
        preview_components_data.append(preview_comp)
        
    return jsonify(
        success=True, 
        components=preview_components_data, 
        total_calculated_cost=float(total_preview_cost.quantize(Decimal("0.01"))),
        tech_card_name=parsed_data.get('tech_card_name', f"Новая техкарта для {product.name}"),
        tech_card_version=parsed_data.get('tech_card_version', DEFAULT_TECH_CARD_VERSION),
        warnings=list(set(parser_warnings))
    )

@app.route('/admin/product/process-techcard-from-modal', methods=['POST'])
@admin_required
def admin_process_techcard_from_modal():
    product_id_str = request.form.get('product_id')
    if not product_id_str or not product_id_str.isdigit():
        return jsonify(success=False, message="ID товара не предоставлен или некорректен.")
    
    product_id = int(product_id_str)
    product = Product.query.get(product_id)
    if not product: 
        return jsonify(success=False, message=f"Продукт с ID {product_id} не найден.")

    tech_card_file = request.files.get('tech_card_excel_file_modal')
    editor_comment_from_form = request.form.get('comment', '').strip()
    desired_status = request.form.get('status', TECH_CARD_STATUS_DRAFT)
    existing_tech_card_id = request.form.get('tech_card_id', type=int)

    current_user = get_current_user()
    current_user_id = current_user.id if current_user else None

    processed_tech_card = None
    parser_errors_for_flash = []
    parser_warnings_for_flash = []

    if tech_card_file and tech_card_file.filename != '':
        if not allowed_file(tech_card_file.filename, 'ALLOWED_EXTENSIONS_EXCEL'):
            return jsonify(success=False, message="Недопустимый тип файла для техкарты.")

        original_filename = secure_filename(tech_card_file.filename)
        unique_prefix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:6]
        saved_filename_on_disk = f"{unique_prefix}_{original_filename}"
        
        filepath_on_disk = os.path.join(current_app.config['UPLOAD_FOLDER_TECH_CARDS_EXCEL'], saved_filename_on_disk)
        db_file_path = saved_filename_on_disk

        try:
            tech_card_file.save(filepath_on_disk)
            current_app.logger.info(f"Файл техкарты сохранен: {filepath_on_disk}")
        except Exception as e:
            current_app.logger.error(f"Ошибка сохранения файла техкарты: {e}", exc_info=True)
            return jsonify(success=False, message=f"Ошибка сохранения файла: {str(e)}")

        parsed_data = parse_excel_data(filepath_on_disk, 
                                       product_sku_hint=product.sku,
                                       tech_card_name_hint=request.form.get('tech_card_name_hint'),
                                       tech_card_version_hint=request.form.get('tech_card_version_hint')) 
        
        if parsed_data:
            parser_errors_for_flash.extend(parsed_data.get('errors', []))
            parser_warnings_for_flash.extend(parsed_data.get('warnings', []))
            if parser_errors_for_flash:
                flash("Критические ошибки при разборе файла техкарты: " + "; ".join(parser_errors_for_flash), "danger")
                for warn in parser_warnings_for_flash: flash(warn, "warning")
                if os.path.exists(filepath_on_disk): os.remove(filepath_on_disk)
                return jsonify(success=False, message="Ошибки парсинга файла: " + "; ".join(parser_errors_for_flash))
        else:
            flash("Не удалось обработать файл техкарты (парсер вернул None).", "danger")
            if os.path.exists(filepath_on_disk): os.remove(filepath_on_disk)
            return jsonify(success=False, message="Ошибка: парсер не смог обработать файл.")

        tech_card_file_info = {
            'original_filename': original_filename, 
            'saved_filename_relative_to_uploads_private': db_file_path
        }
        
        processed_tech_card, processing_errors = _process_techcard_data_and_update_db(
            parsed_data, product, tech_card_file_info, current_user_id, desired_status, editor_comment_from_form
        )
        parser_errors_for_flash.extend(processing_errors)

    elif existing_tech_card_id:
        tech_card_to_update = TechCard.query.get(existing_tech_card_id)
        if tech_card_to_update and tech_card_to_update.product_id == product.id:
            if desired_status in [TECH_CARD_STATUS_APPROVED, TECH_CARD_STATUS_PROCESSED] and \
               tech_card_to_update.status == TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES:
                
                materials_still_without_price = False
                for comp in tech_card_to_update.components:
                    if comp.raw_material_item.price is None or comp.raw_material_item.price <= Decimal('0'):
                        materials_still_without_price = True
                        break
                if materials_still_without_price:
                    flash(f"Невозможно установить статус '{desired_status}'. Техкарта все еще содержит компоненты без цен.", "danger")
                else: 
                    tech_card_to_update.status = desired_status
                    flash("Все цены для компонентов техкарты теперь указаны.", "info")
            else:
                 tech_card_to_update.status = desired_status

            if editor_comment_from_form: 
                tech_card_to_update.description = editor_comment_from_form
            
            tech_card_to_update.updated_at = datetime.now(timezone.utc)
            if tech_card_to_update.status in [TECH_CARD_STATUS_APPROVED, TECH_CARD_STATUS_PROCESSED]:
                if tech_card_to_update.total_cost is not None:
                    product.cost_price = tech_card_to_update.total_cost
                    product.cost_price_source = f"Техкарта v{tech_card_to_update.version or '?'} от {tech_card_to_update.updated_at.strftime('%d.%m.%Y %H:%M')} ({tech_card_to_update.status})"
                    recalculate_all_product_prices(product)
                    current_app.logger.info(f"Себестоимость продукта ID {product.id} обновлена (статус изменен) на {product.cost_price} из техкарты ID {tech_card_to_update.id}")

            db.session.add(tech_card_to_update)
            processed_tech_card = tech_card_to_update
            current_app.logger.info(f"Обновлен статус/комментарий для техкарты ID {existing_tech_card_id} на '{desired_status}'.")
        else:
            flash("Техкарта для обновления не найдена или не принадлежит этому товару.", "danger")
            return jsonify(success=False, message="Техкарта для обновления не найдена.")
    else:
        flash("Файл техкарты не был загружен, и не указана существующая техкарта для обновления.", "warning")
        return jsonify(success=False, message="Файл не загружен и ID существующей техкарты не указан.")

    if not processed_tech_card:
        final_message = "Не удалось обработать техкарту."
        if parser_errors_for_flash:
            final_message += " Ошибки: " + "; ".join(parser_errors_for_flash)
        flash(final_message, "danger")
        return jsonify(success=False, message=final_message)

    try:
        db.session.commit()
        flash(f"Техкарта '{processed_tech_card.name}' (v{processed_tech_card.version}) успешно обработана со статусом '{processed_tech_card.status}'.", 'success')
        for warn in parser_warnings_for_flash: flash(warn, "warning")

        active_tc_for_main_page = product.active_tech_card 
        tech_card_components_for_snippet = []
        if active_tc_for_main_page:
            tech_card_components_for_snippet = active_tc_for_main_page.components.order_by(TechCardComponent.id).all()

        tech_card_info_html_snippet = render_template(
            'admin/_tech_card_summary_snippet.html', 
            active_tech_card=active_tc_for_main_page, 
            tech_card_components=tech_card_components_for_snippet,
            TECH_CARD_STATUS_APPROVED=TECH_CARD_STATUS_APPROVED,
            TECH_CARD_STATUS_PENDING_ACCOUNTANT=TECH_CARD_STATUS_PENDING_ACCOUNTANT,
            TECH_CARD_STATUS_PENDING_MANAGER=TECH_CARD_STATUS_PENDING_MANAGER,
            TECH_CARD_STATUS_PROCESSED=TECH_CARD_STATUS_PROCESSED,
            TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES=TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES,
            TECH_CARD_STATUS_DRAFT=TECH_CARD_STATUS_DRAFT,
            TECH_CARD_STATUS_REJECTED_ACCOUNTANT=TECH_CARD_STATUS_REJECTED_ACCOUNTANT,
            TECH_CARD_STATUS_REJECTED_MANAGER=TECH_CARD_STATUS_REJECTED_MANAGER,
            TECH_CARD_STATUS_ARCHIVED=TECH_CARD_STATUS_ARCHIVED
        )
        
        return jsonify(
            success=True, 
            message=f"Техкарта успешно обработана.",
            new_cost_price=float(product.cost_price) if product.cost_price is not None else 0.0, 
            cost_price_source=product.cost_price_source, 
            tech_card_info_html=tech_card_info_html_snippet,
            tech_card_id = processed_tech_card.id,
            tech_card_status = processed_tech_card.status
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка commit при обработке техкарты из модала: {e}", exc_info=True)
        flash(f"Ошибка сохранения данных в БД: {str(e)}", "danger")
        return jsonify(success=False, message=f"Ошибка сохранения в БД: {str(e)}")

# --- Маршруты для страниц админ-панели ---

@app.route('/admin/products', methods=['GET'])
@admin_required
def admin_products():
    products_query = Product.query
    
    search_term = request.args.get('search')
    category_filter = request.args.get('category_id') 
    availability_filter = request.args.get('availability_status')
    techcard_status_filter = request.args.get('techcard_status')


    if search_term:
        products_query = products_query.filter(or_(
            Product.name.ilike(f"%{search_term}%"),
            Product.sku.ilike(f"%{search_term}%")
        ))
    if category_filter:
        products_query = products_query.filter(Product.category_id == category_filter)
    if availability_filter:
        products_query = products_query.filter(Product.availability_status == availability_filter)
    
    if techcard_status_filter:
        if techcard_status_filter == "no_card":
             products_query = products_query.outerjoin(TechCard, 
                                        (Product.id == TechCard.product_id) & 
                                        (TechCard.status != TECH_CARD_STATUS_ARCHIVED)
                                    ).filter(TechCard.id == None)
        else:
            products_query = products_query.join(TechCard).filter(TechCard.status == techcard_status_filter)


    products = products_query.order_by(Product.name).all()
    total_products_count = len(products) 

    categories = Category.query.order_by(Category.name).all()
    
    return render_template('admin/admin_products.html', 
                           products=products, 
                           page_title="Управление Товарами",
                           total_products_count=total_products_count,
                           categories=categories,
                           TECH_CARD_STATUS_DRAFT=TECH_CARD_STATUS_DRAFT,
                           TECH_CARD_STATUS_PENDING_ACCOUNTANT=TECH_CARD_STATUS_PENDING_ACCOUNTANT,
                           TECH_CARD_STATUS_APPROVED=TECH_CARD_STATUS_APPROVED,
                           TECH_CARD_STATUS_REJECTED_ACCOUNTANT=TECH_CARD_STATUS_REJECTED_ACCOUNTANT, 
                           TECH_CARD_STATUS_ARCHIVED=TECH_CARD_STATUS_ARCHIVED,
                           TECH_CARD_STATUS_PENDING_MANAGER=TECH_CARD_STATUS_PENDING_MANAGER,
                           TECH_CARD_STATUS_REJECTED_MANAGER=TECH_CARD_STATUS_REJECTED_MANAGER,
                           TECH_CARD_STATUS_PROCESSED=TECH_CARD_STATUS_PROCESSED,
                           TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES=TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES
                           )

@app.route('/admin/product/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    categories = Category.query.order_by(Category.name).all()
    product_data_for_template = request.form if request.method == 'POST' else {} 

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            sku = request.form.get('sku')
            category_id_str = request.form.get('category_id')

            if not name or not sku or not category_id_str:
                flash('Наименование, Артикул и Категория обязательны.', 'danger')
                return render_template('admin/admin_product_edit.html', page_title="Добавление нового товара", product_data=request.form, categories=categories, product=None, active_tech_card=None, tech_card_components=None, TECH_CARD_STATUS_DRAFT=TECH_CARD_STATUS_DRAFT, TECH_CARD_STATUS_PENDING_ACCOUNTANT=TECH_CARD_STATUS_PENDING_ACCOUNTANT, TECH_CARD_STATUS_APPROVED=TECH_CARD_STATUS_APPROVED, TECH_CARD_STATUS_PROCESSED=TECH_CARD_STATUS_PROCESSED, TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES=TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES)
            
            category_id = int(category_id_str)
            if Product.query.filter_by(sku=sku).first():
                flash(f'Товар с артикулом {sku} уже существует.', 'danger')
                return render_template('admin/admin_product_edit.html', page_title="Добавление нового товара", product_data=request.form, categories=categories, product=None, active_tech_card=None, tech_card_components=None, TECH_CARD_STATUS_DRAFT=TECH_CARD_STATUS_DRAFT, TECH_CARD_STATUS_PENDING_ACCOUNTANT=TECH_CARD_STATUS_PENDING_ACCOUNTANT, TECH_CARD_STATUS_APPROVED=TECH_CARD_STATUS_APPROVED, TECH_CARD_STATUS_PROCESSED=TECH_CARD_STATUS_PROCESSED, TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES=TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES)

            new_product = Product(
                name=name, 
                sku=sku, 
                slug=secure_filename(name.lower().replace(' ', '-').replace('_', '-')), 
                category_id=category_id,
                description=request.form.get('description'), 
                short_description=request.form.get('short_description'),
                cost_price=get_decimal_from_form('cost_price'),
                markup_percentage=get_decimal_from_form('markup_percentage'),
                discounted_price=get_decimal_from_form('discounted_price'),
                wholesale_markup_percentage=get_decimal_from_form('wholesale_markup_percentage'),
                dealer_markup_percentage=get_decimal_from_form('dealer_markup_percentage'),
                availability_status=request.form.get('availability_status', 'in_stock'),
                is_published=request.form.get('is_published') == 'true',
                weight=get_decimal_from_form('weight'),
                dimensions=request.form.get('dimensions'),
                specifications=request.form.get('specifications_json'),
                seo_title=request.form.get('seo_title'),
                seo_description=request.form.get('seo_description'),
                seo_keywords=request.form.get('seo_keywords'),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            recalculate_all_product_prices(new_product)
            
            manual_retail_price = get_decimal_from_form('price')
            if manual_retail_price is not None and (new_product.cost_price is None or new_product.cost_price == Decimal('0.00')):
                new_product.price = manual_retail_price
            
            db.session.add(new_product)
            db.session.flush()

            saved_image_urls = save_product_images_fs(new_product.id, new_product.sku)
            update_product_image_records_db(
                new_product, 
                saved_image_urls, 
                request.form.get('image_order'), 
                request.form.get('main_image_filename'), 
                request.form.getlist('deleted_image_ids[]')
            )
            
            db.session.commit()
            flash(f'Товар "{new_product.name}" успешно добавлен!', 'success')
            current_app.logger.info(f"Добавлен новый товар ID {new_product.id}, SKU {new_product.sku}")
            return redirect(url_for('admin_edit_product', product_id=new_product.id))

        except IntegrityError as e: 
            db.session.rollback()
            flash(f'Ошибка целостности данных: {e.orig}. Возможно, такой артикул или slug уже существует.', 'danger')
            current_app.logger.error(f"Ошибка целостности при добавлении товара: {e}", exc_info=True)
        except Exception as e: 
            db.session.rollback()
            flash(f'Непредвиденная ошибка при добавлении товара: {str(e)}', 'danger')
            current_app.logger.error(f"Ошибка добавления товара: {e}", exc_info=True)
        
        return render_template('admin/admin_product_edit.html', page_title="Добавление нового товара", product_data=request.form, categories=categories, product=None, active_tech_card=None, tech_card_components=None, TECH_CARD_STATUS_DRAFT=TECH_CARD_STATUS_DRAFT, TECH_CARD_STATUS_PENDING_ACCOUNTANT=TECH_CARD_STATUS_PENDING_ACCOUNTANT, TECH_CARD_STATUS_APPROVED=TECH_CARD_STATUS_APPROVED, TECH_CARD_STATUS_PROCESSED=TECH_CARD_STATUS_PROCESSED, TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES=TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES)

    return render_template('admin/admin_product_edit.html', page_title="Добавление нового товара", product=None, categories=categories, active_tech_card=None, tech_card_components=None, product_data=product_data_for_template, TECH_CARD_STATUS_DRAFT=TECH_CARD_STATUS_DRAFT, TECH_CARD_STATUS_PENDING_ACCOUNTANT=TECH_CARD_STATUS_PENDING_ACCOUNTANT, TECH_CARD_STATUS_APPROVED=TECH_CARD_STATUS_APPROVED, TECH_CARD_STATUS_PROCESSED=TECH_CARD_STATUS_PROCESSED, TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES=TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES)

@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    categories = Category.query.order_by(Category.name).all()
    
    active_tech_card = product.active_tech_card 
    tech_card_components_list = active_tech_card.components.order_by(TechCardComponent.id).all() if active_tech_card else []

    if request.method == 'POST':
        try:
            product.name = request.form.get('name', product.name)
            new_sku = request.form.get('sku', product.sku).strip()
            if new_sku != product.sku:
                if Product.query.filter(Product.id != product.id, Product.sku == new_sku).first():
                    flash(f'Товар с артикулом {new_sku} уже существует.', 'danger')
                    return render_template('admin/admin_product_edit.html', page_title=f"Редактирование: {product.name}", product=product, product_data=request.form, categories=categories, active_tech_card=active_tech_card, tech_card_components=tech_card_components_list, TECH_CARD_STATUS_DRAFT=TECH_CARD_STATUS_DRAFT, TECH_CARD_STATUS_PENDING_ACCOUNTANT=TECH_CARD_STATUS_PENDING_ACCOUNTANT, TECH_CARD_STATUS_APPROVED=TECH_CARD_STATUS_APPROVED, TECH_CARD_STATUS_PROCESSED=TECH_CARD_STATUS_PROCESSED, TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES=TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES)
            
            product.sku = new_sku
            product.slug = secure_filename(product.name.lower().replace(' ', '-').replace('_','-'))
            product.category_id = request.form.get('category_id', product.category_id, type=int)
            product.description = request.form.get('description', product.description)
            product.short_description = request.form.get('short_description', product.short_description)
            
            product.cost_price = get_decimal_from_form('cost_price', default_value=product.cost_price)
            product.markup_percentage = get_decimal_from_form('markup_percentage', default_value=product.markup_percentage)
            product.discounted_price = get_decimal_from_form('discounted_price', default_value=product.discounted_price)
            product.wholesale_markup_percentage = get_decimal_from_form('wholesale_markup_percentage', default_value=product.wholesale_markup_percentage)
            product.dealer_markup_percentage = get_decimal_from_form('dealer_markup_percentage', default_value=product.dealer_markup_percentage)
            
            product.availability_status = request.form.get('availability_status', product.availability_status)
            product.is_published = request.form.get('is_published') == 'true'
            product.weight = get_decimal_from_form('weight', default_value=product.weight)
            product.dimensions = request.form.get('dimensions', product.dimensions)
            
            spec_json = request.form.get('specifications_json')
            if spec_json: product.specifications = spec_json
            
            product.seo_title = request.form.get('seo_title', product.seo_title)
            product.seo_description = request.form.get('seo_description', product.seo_description)
            product.seo_keywords = request.form.get('seo_keywords', product.seo_keywords)
            product.updated_at = datetime.now(timezone.utc)

            saved_image_urls = save_product_images_fs(product.id, product.sku)
            update_product_image_records_db(
                product, 
                saved_image_urls, 
                request.form.get('image_order'), 
                request.form.get('main_image_filename'),
                request.form.getlist('deleted_image_ids[]')
            )
            
            recalculate_all_product_prices(product)
            
            manual_retail_price = get_decimal_from_form('price')
            if manual_retail_price is not None:
                product.price = manual_retail_price 
                if product.cost_price and product.cost_price > Decimal('0.00'):
                    product.markup_percentage = ((manual_retail_price - product.cost_price) / product.cost_price) * 100
                elif product.cost_price == Decimal('0.00') or product.cost_price is None :
                    product.markup_percentage = None
            
            db.session.commit()
            flash(f'Товар "{product.name}" успешно обновлен!', 'success')
            current_app.logger.info(f"Обновлен товар ID {product.id}, SKU {product.sku}")
            return redirect(url_for('admin_edit_product', product_id=product.id))

        except IntegrityError as e: 
            db.session.rollback()
            flash(f'Ошибка целостности данных: {e.orig}. Возможно, такой артикул или slug уже существует.', 'danger')
            current_app.logger.error(f"Ошибка целостности при обновлении товара ID {product_id}: {e}", exc_info=True)
        except Exception as e: 
            db.session.rollback()
            flash(f'Непредвиденная ошибка при обновлении товара: {str(e)}', 'danger')
            current_app.logger.error(f"Ошибка обновления товара ID {product_id}: {e}", exc_info=True)
        
        return render_template('admin/admin_product_edit.html', page_title=f"Редактирование: {product.name}", product=product, product_data=request.form, categories=categories, active_tech_card=active_tech_card, tech_card_components=tech_card_components_list, TECH_CARD_STATUS_DRAFT=TECH_CARD_STATUS_DRAFT, TECH_CARD_STATUS_PENDING_ACCOUNTANT=TECH_CARD_STATUS_PENDING_ACCOUNTANT, TECH_CARD_STATUS_APPROVED=TECH_CARD_STATUS_APPROVED, TECH_CARD_STATUS_PROCESSED=TECH_CARD_STATUS_PROCESSED, TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES=TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES)

    return render_template('admin/admin_product_edit.html', 
                           page_title=f"Редактирование: {product.name}", 
                           product=product, 
                           categories=categories, 
                           active_tech_card=active_tech_card, 
                           tech_card_components=tech_card_components_list,
                           product_data=None,
                           TECH_CARD_STATUS_DRAFT=TECH_CARD_STATUS_DRAFT,
                           TECH_CARD_STATUS_PENDING_ACCOUNTANT=TECH_CARD_STATUS_PENDING_ACCOUNTANT,
                           TECH_CARD_STATUS_APPROVED=TECH_CARD_STATUS_APPROVED,
                           TECH_CARD_STATUS_PROCESSED=TECH_CARD_STATUS_PROCESSED,
                           TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES=TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES,
                           TECH_CARD_STATUS_PENDING_MANAGER=TECH_CARD_STATUS_PENDING_MANAGER,
                           TECH_CARD_STATUS_REJECTED_ACCOUNTANT=TECH_CARD_STATUS_REJECTED_ACCOUNTANT,
                           TECH_CARD_STATUS_REJECTED_MANAGER=TECH_CARD_STATUS_REJECTED_MANAGER,
                           TECH_CARD_STATUS_ARCHIVED=TECH_CARD_STATUS_ARCHIVED
                           )

@app.route('/admin/raw-materials', methods=['GET', 'POST'])
@admin_required
def admin_raw_materials():
    if request.method == 'POST': # Логика добавления нового материала
        name = request.form.get('material-name') # Исправлено на соответствие ID в HTML
        sku = request.form.get('material-sku')
        unit = request.form.get('material-unit')
        price_str = request.form.get('material-price', '0').replace(',', '.')
        # supplier = request.form.get('material-supplier') # Если нужно сохранять поставщика
        
        if not name or not unit:
            flash("Наименование и единица измерения обязательны для нового материала.", "danger")
        else:
            try:
                price = Decimal(price_str)
                if price < 0:
                    flash("Цена не может быть отрицательной.", "danger")
                else:
                    if sku and RawMaterial.query.filter_by(sku=sku).first():
                        flash(f"Материал с артикулом '{sku}' уже существует.", "warning")
                    elif RawMaterial.query.filter(func.lower(RawMaterial.name) == func.lower(name)).first():
                        flash(f"Материал с наименованием '{name}' уже существует.", "warning")
                    else:
                        new_material = RawMaterial(
                            name=name, 
                            sku=sku if sku else None, 
                            unit_of_measurement=unit, 
                            price=price,
                            # supplier_name=supplier, # Если есть поле в модели
                            updated_at=datetime.now(timezone.utc)
                        )
                        db.session.add(new_material)
                        db.session.commit()
                        flash(f"Материал '{name}' успешно добавлен.", "success")
                        current_app.logger.info(f"Добавлен новый материал: {name} (SKU: {sku})")
                        return redirect(url_for('admin_raw_materials'))
            except InvalidOperation:
                flash("Некорректный формат цены.", "danger")
            except IntegrityError as e:
                db.session.rollback()
                flash(f"Ошибка добавления материала (возможно, дубликат): {e.orig}", "danger")
                current_app.logger.error(f"Ошибка IntegrityError при добавлении сырья: {e}", exc_info=True)
            except Exception as e:
                db.session.rollback()
                flash(f"Непредвиденная ошибка: {str(e)}", "danger")
                current_app.logger.error(f"Ошибка при добавлении сырья: {e}", exc_info=True)

    materials = RawMaterial.query.order_by(RawMaterial.name).all()
    return render_template('admin/admin_raw_materials.html', 
                           materials=materials, 
                           page_title="Сырьё и Закупочные Цены",
                           total_materials_count=len(materials)) # Передаем количество

@app.route('/admin/raw-material/update-price/<int:material_id>', methods=['POST'])
@admin_required
def admin_update_raw_material_price(material_id): # Этот маршрут, возможно, не нужен, если редактирование идет через модальное окно
    material = RawMaterial.query.get_or_404(material_id)
    new_price_str = request.form.get('price') # Убедитесь, что имя поля 'price'
    if new_price_str is None:
        flash('Цена не была предоставлена.', 'danger')
        return redirect(url_for('admin_raw_materials'))
    try:
        new_price_str = new_price_str.replace(',', '.')
        new_price = Decimal(new_price_str)
        if new_price < 0: 
            flash('Цена не может быть отрицательной.', 'danger')
        else:
            material.price = new_price
            material.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            flash(f'Цена для материала "{material.name}" обновлена.', 'success')
            current_app.logger.info(f"Обновлена цена для сырья ID {material_id} на {new_price}")
    except InvalidOperation: 
        flash('Некорректный формат цены.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при обновлении цены: {str(e)}', 'danger')
        current_app.logger.error(f"Ошибка обновления цены сырья ID {material_id}: {e}", exc_info=True)
    return redirect(url_for('admin_raw_materials'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard(): 
    total_products = Product.query.count()
    total_tech_cards = TechCard.query.count()
    pending_approvals_count = ApprovalTask.query.filter(
        or_(
            ApprovalTask.status == TECH_CARD_STATUS_PENDING_ACCOUNTANT,
            ApprovalTask.status == TECH_CARD_STATUS_PENDING_MANAGER,
            ApprovalTask.status == 'Ожидает' 
        )
    ).count()
    
    # Данные для графиков (заглушки)
    sales_data = {
        "labels": ["Янв", "Фев", "Мар", "Апр", "Май", "Июн"],
        "values": [120, 150, 180, 130, 160, 200]
    }
    product_categories_data = {
        "labels": ["Тумбы", "Зеркала", "Пеналы", "Комплекты"],
        "values": [45, 30, 15, 10]
    }
    
    return render_template('admin/admin_dashboard.html', 
                           page_title="Дашборд",
                           total_products=total_products,
                           total_tech_cards=total_tech_cards,
                           pending_approvals_count=pending_approvals_count,
                           sales_data=sales_data,
                           product_categories_data=product_categories_data
                           )

@app.route('/admin/techcard-list')
@admin_required
def admin_techcard_list(): 
    tech_cards_query = TechCard.query.join(Product, TechCard.product_id == Product.id)
    
    search_term = request.args.get('search_product')
    status_filter = request.args.get('status_techcard')
    category_filter = request.args.get('category_id_techcard') 

    if search_term:
        tech_cards_query = tech_cards_query.filter(or_(
            Product.name.ilike(f"%{search_term}%"),
            Product.sku.ilike(f"%{search_term}%")
        ))
    if status_filter:
        tech_cards_query = tech_cards_query.filter(TechCard.status == status_filter)
    if category_filter:
        tech_cards_query = tech_cards_query.filter(Product.category_id == category_filter)
        
    tech_cards = tech_cards_query.order_by(Product.name, TechCard.updated_at.desc()).all()
    total_techcards_count = len(tech_cards) 

    categories = Category.query.order_by(Category.name).all()

    return render_template('admin/admin_techcard_list.html', 
                           tech_cards=tech_cards, 
                           page_title="Управление Техкартами",
                           total_techcards_count=total_techcards_count,
                           categories=categories, 
                           TECH_CARD_STATUS_DRAFT=TECH_CARD_STATUS_DRAFT,
                           TECH_CARD_STATUS_PENDING_ACCOUNTANT=TECH_CARD_STATUS_PENDING_ACCOUNTANT,
                           TECH_CARD_STATUS_APPROVED=TECH_CARD_STATUS_APPROVED,
                           TECH_CARD_STATUS_REJECTED_ACCOUNTANT=TECH_CARD_STATUS_REJECTED_ACCOUNTANT,
                           TECH_CARD_STATUS_PENDING_MANAGER=TECH_CARD_STATUS_PENDING_MANAGER,
                           TECH_CARD_STATUS_REJECTED_MANAGER=TECH_CARD_STATUS_REJECTED_MANAGER,
                           TECH_CARD_STATUS_PROCESSED=TECH_CARD_STATUS_PROCESSED,
                           TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES=TECH_CARD_STATUS_PROCESSED_NEEDS_PRICES,
                           TECH_CARD_STATUS_ARCHIVED=TECH_CARD_STATUS_ARCHIVED
                           )

@app.route('/admin/approval-tasks')
@admin_required
def admin_approval_tasks(): 
    # TODO: Заменить моковые данные на реальный запрос к ApprovalTask
    # tasks = ApprovalTask.query.filter(ApprovalTask.status.startswith('Ожидает')).order_by(ApprovalTask.created_at.desc()).all()
    mock_user1 = User(username='Петров П.П.')
    mock_user2 = User(username='Сидорова А.А.')
    mock_tasks = [
        {'id': 1, 'entity_type': 'TechCard', 'entity_id': 101, 
         'tech_card': TechCard(product=Product(name='Тумба "Фест" 60 с раковиной', sku='WS-FST60-WHT')), 
         'status': 'Ожидает бухгалтера', 'created_by_user': mock_user1, 'created_at': datetime(2025, 5, 18, 10, 30), 'description': 'Новая техкарта'},
        {'id': 2, 'entity_type': 'TechCard', 'entity_id': 102,
         'tech_card': TechCard(product=Product(name='Зеркало "Орион" 80 LED', sku='WS-ZER80-LED')),
         'status': 'Ожидает руководителя', 'created_by_user': mock_user2, 'created_at': datetime(2025, 5, 17, 16, 15), 'description': 'Обновление техкарты'},
    ]
    return render_template('admin/admin_approval_tasks_list.html', 
                           tasks=mock_tasks, 
                           page_title="Задачи на согласование Техкарт")

@app.route('/admin/approval-task/<int:task_id>')
@admin_required
def admin_approval_task_detail(task_id):
    # TODO: Заменить моковые данные на реальный запрос
    if task_id == 1:
        mock_task_detail = {
            'id': 1, 'product_name': 'Тумба "Фест" 60 с раковиной', 'product_sku': 'WS-FST60-WHT',
            'editor_name': 'Петров П.П.', 'submission_date': '18.05.2025 10:30', 'change_type': 'Новая техкарта',
            'editor_comment': 'Первичная загрузка техкарты. Прошу проверить.',
            'current_retail_price': None, 'is_update': False, 'current_tech_card_info': None,
            'new_tech_card_components': [ 
                {'num': 1, 'article': "ЛДСП-Б-16", 'name': "ЛДСП Белый гладкий 16мм", 'quantity': Decimal('1.25'), 'unit': "кв.м"},
                {'num': 2, 'article': "ZER-AGC-04-NEW", 'name': "Зеркало 4мм AGC (Новый поставщик)", 'quantity': Decimal('0.48'), 'unit': "кв.м"},
                {'num': 3, 'article': "NO-PRICE-YET", 'name': "Фурнитура XYZ (без цены)", 'quantity': Decimal('1'), 'unit': "компл."},
            ],
            'tech_card_file_url': '#example_new_techcard.xlsx' 
        }
    elif task_id == 2:
         mock_task_detail = {
            'id': 2, 'product_name': 'Зеркало "Орион" 80 LED', 'product_sku': 'WS-ZER80-LED',
            'editor_name': 'Сидорова А.А.', 'submission_date': '17.05.2025 16:15', 'change_type': 'Обновление техкарты',
            'editor_comment': 'Замена материала подсветки.',
            'current_retail_price': Decimal('12000.00'), 'is_update': True,
            'current_tech_card_info': { 'date': '10.01.2025', 'material_cost': Decimal('4800.00'), 'retail_price': Decimal('12000.00'), 'file_name': 'techcard_orion80_v1.xlsx' },
            'new_tech_card_components': [
                {'num': 1, 'article': "ZER-AGC-04", 'name': "Зеркало 4мм AGC", 'quantity': Decimal('0.96'), 'unit': "кв.м"},
            ],
            'tech_card_file_url': '#example_updated_techcard.xlsx'
        }
    else:
        flash(f"Задача с ID {task_id} не найдена (моковые данные).", "warning")
        return redirect(url_for('admin_approval_tasks'))
    
    task_data_json = json.dumps(mock_task_detail, default=lambda o: str(o) if isinstance(o, Decimal) else o)

    return render_template('admin/admin_techcard_approval_detail.html', 
                           task_data_json=task_data_json, 
                           page_title=f"Согласование: {mock_task_detail['product_name']}")


@app.route('/admin/dealers-list') 
@admin_required
def admin_dealers_list(): 
    dealers = Dealer.query.order_by(Dealer.name).all() if db.inspect(app).has_table('dealers') else []
    return render_template('admin/admin_dealers_list.html', 
                           dealers=dealers, 
                           page_title="Дилеры и Оптовики")

@app.route('/admin/users')
@admin_required
def admin_users(): 
    users = User.query.order_by(User.username).all()
    return render_template('admin/admin_users.html', users=users, page_title="Пользователи")

@app.route('/') 
def index(): 
    return "Главная страница сайта (в разработке)" 

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all() 
            app.logger.info("База данных и таблицы успешно созданы/проверены!")

            if not User.query.filter_by(role=USER_ROLE_ADMIN).first():
                try:
                    admin_password_hash = generate_password_hash("adminpassword", method='pbkdf2:sha256')
                    admin_user = User(
                        username="admin", 
                        email="admin@example.com", 
                        password_hash=admin_password_hash, 
                        role=USER_ROLE_ADMIN,
                        is_admin=True,
                        is_active=True,
                        first_name="Администратор"
                    )
                    db.session.add(admin_user)
                    db.session.commit()
                    app.logger.info(f"Тестовый администратор 'admin' добавлен. ID: {admin_user.id}.")
                except Exception as e_admin:
                    db.session.rollback()
                    app.logger.error(f"Ошибка при добавлении тестового администратора: {e_admin}", exc_info=True)
            
            if not Category.query.first():
                try:
                    categories_to_add = [
                        Category(name="Тумбы с раковиной", slug="tumbi-s-rakovinoy"), 
                        Category(name="Зеркала и шкафы", slug="zerkala-i-shkafi"),
                        Category(name="Пеналы", slug="penali"), 
                        Category(name="Комплекты мебели", slug="komplekti-mebeli"),
                        Category(name="Аксессуары", slug="aksessuari")
                    ]
                    db.session.add_all(categories_to_add)
                    db.session.commit()
                    app.logger.info("Тестовые категории добавлены.")
                except Exception as e_cat:
                    db.session.rollback()
                    app.logger.error(f"Ошибка при добавлении тестовых категорий: {e_cat}", exc_info=True)
        except Exception as e_db:
            app.logger.critical(f"Критическая ошибка при создании таблиц БД: {e_db}", exc_info=True)
            exit()

    app.run(debug=True, port=5001)
