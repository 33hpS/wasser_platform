# F:\МебельПрайсПро\my_app\xlsx_parser.py
# или F:\МебельПрайсПро\xlsx_parser.py, в зависимости от структуры импорта в app.py

import openpyxl
from decimal import Decimal, InvalidOperation
import os
import logging

# Настройка базового логгера
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO) # Установите INFO или DEBUG по необходимости

# --- Конфигурация парсера ---
DEFAULT_TECH_CARD_VERSION = "1.0"

EXPECTED_HEADERS_COMPONENT = {
    'sku': ['Артикул', 'Артикул материала', 'SKU', 'Код'],
    'name': ['Наименование материала', 'Наименование', 'Материал', 'Описание'],
    'quantity': ['Количество', 'Кол-во', 'Qty'],
    'unit': ['Единица измерения', 'Ед.изм.', 'Ед.', 'Unit'],
    'price_optional': ['Цена за ед.', 'Цена', 'Price'] # Опционально, если цена есть в Excel
}

METADATA_CELLS = {
    'product_sku': None, # Например, 'A1'
    'tech_card_name': None, # Например, 'B1'
    'tech_card_version': None, # Например, 'C1'
}

def find_header_row_and_cols(sheet, expected_headers_map, header_search_rows=5):
    """
    Ищет строку с заголовками и сопоставляет столбцы с ожидаемыми заголовками.
    Возвращает (header_row_index, column_map) или (None, {}).
    """
    for row_idx in range(1, min(header_search_rows + 1, sheet.max_row + 1)):
        current_row_values = {
            str(cell.value).strip().lower(): cell.column_letter
            for cell in sheet[row_idx] if cell.value is not None
        }
        
        found_cols = {}
        matched_header_count = 0
        
        for internal_name, possible_headers in expected_headers_map.items():
            for header_text in possible_headers:
                if header_text.lower() in current_row_values:
                    found_cols[internal_name] = current_row_values[header_text.lower()]
                    matched_header_count +=1
                    break 

        # Условие для определения строки заголовков (можно адаптировать)
        # Например, требуем как минимум 'name' и 'quantity'
        required_matches_for_detection = sum(1 for key in ['name', 'quantity'] if key in expected_headers_map)
        
        if matched_header_count >= required_matches_for_detection:
            # Дополнительная проверка на наличие всех *обязательных* для парсинга колонок
            essential_keys_for_parsing = ['name', 'quantity', 'unit']
            if all(key in found_cols for key in essential_keys_for_parsing if key in expected_headers_map):
                logger.info(f"Строка заголовков найдена на строке {row_idx}. Сопоставленные столбцы: {found_cols}")
                return row_idx, found_cols
            else:
                logger.warning(f"На строке {row_idx} найдены некоторые заголовки ({found_cols.keys()}), но не все основные ({essential_keys_for_parsing}). Пропускаем.")
    
    logger.warning("Строка с ожидаемыми заголовками не найдена в пределах первых {} строк.".format(header_search_rows))
    return None, {}

def get_cell_value_str(sheet, cell_address):
    """Безопасно получает строковое значение ячейки."""
    if cell_address:
        try:
            val = sheet[cell_address].value
            return str(val).strip() if val is not None else None
        except KeyError: # Если адрес ячейки некорректен (например, 'A0')
            logger.warning(f"Некорректный адрес ячейки для метаданных: {cell_address}")
            return None
    return None

def parse_excel_data(filepath, product_sku_hint=None, tech_card_name_hint=None, tech_card_version_hint=None):
    """
    Парсит данные из Excel-файла техкарты.
    Возвращает dict с данными или None при критической ошибке.
    """
    try:
        workbook = openpyxl.load_workbook(filepath, data_only=True)
        sheet = workbook.active
    except Exception as e:
        logger.error(f"Ошибка при открытии Excel файла {filepath}: {e}", exc_info=True)
        return None

    parsed_components = []
    errors = []
    warnings = []
    
    # 1. Извлечение метаданных
    product_sku_from_cell = get_cell_value_str(sheet, METADATA_CELLS.get('product_sku'))
    tech_card_name_from_cell = get_cell_value_str(sheet, METADATA_CELLS.get('tech_card_name'))
    tech_card_version_from_cell = get_cell_value_str(sheet, METADATA_CELLS.get('tech_card_version'))

    product_sku = product_sku_from_cell or product_sku_hint
    if not product_sku:
        # Попытка извлечь из имени файла (можно улучшить эту логику)
        filename_no_ext = os.path.splitext(os.path.basename(filepath))[0]
        if "_" in filename_no_ext:
            parts = filename_no_ext.split('_')
            if len(parts) > 1 : product_sku = parts[1] # Пример: Техкарта_SKU123...
        if not product_sku:
            product_sku = f"SKU_НЕ_ОПРЕДЕЛЕН_{filename_no_ext[:15]}"
            warnings.append(f"Артикул продукта не удалось определить. Использовано: '{product_sku}'.")
        else:
            warnings.append(f"Артикул продукта '{product_sku}' извлечен из имени файла/подсказки.")
            
    tech_card_name = tech_card_name_from_cell or tech_card_name_hint
    if not tech_card_name:
        tech_card_name = f"Техкарта для {product_sku}"
        warnings.append(f"Имя техкарты сгенерировано: '{tech_card_name}'.")

    tech_card_version = tech_card_version_from_cell or tech_card_version_hint or DEFAULT_TECH_CARD_VERSION
    if not (tech_card_version_from_cell or tech_card_version_hint):
           warnings.append(f"Версия техкарты установлена по умолчанию: '{tech_card_version}'.")

    # 2. Поиск заголовков и определение столбцов компонентов
    header_row_idx, col_map = find_header_row_and_cols(sheet, EXPECTED_HEADERS_COMPONENT)

    if not header_row_idx: # find_header_row_and_cols уже залогировал ошибку
        errors.append("Не удалось найти строку заголовков для компонентов.")
        # Возвращаем то, что успели собрать (метаданные) и ошибки
        return {
            'product_sku': product_sku, 'tech_card_name': tech_card_name,
            'tech_card_version': tech_card_version, 'components': [],
            'errors': errors, 'warnings': warnings
        }
    
    data_start_row = header_row_idx + 1

    # 3. Парсинг компонентов
    for row_num in range(data_start_row, sheet.max_row + 1):
        component_data = {}
        
        sku_val = sheet[f'{col_map.get("sku")}{row_num}'].value if col_map.get("sku") else None
        name_val = sheet[f'{col_map.get("name")}{row_num}'].value if col_map.get("name") else None
        qty_val = sheet[f'{col_map.get("quantity")}{row_num}'].value if col_map.get("quantity") else None
        unit_val = sheet[f'{col_map.get("unit")}{row_num}'].value if col_map.get("unit") else None
        price_val = sheet[f'{col_map.get("price_optional")}{row_num}'].value if col_map.get("price_optional") else None

        if all(val is None for val in [sku_val, name_val, qty_val, unit_val]):
            continue # Пропускаем полностью пустые строки
        
        component_sku = str(sku_val).strip() if sku_val is not None else None
        component_name = str(name_val).strip() if name_val is not None else None
        
        if not component_name and not component_sku:
            warnings.append(f"Строка {row_num}: Пропущена (отсутствует наименование и артикул).")
            continue
        
        if component_name is None and component_sku is not None:
            component_name = component_sku 
            warnings.append(f"Строка {row_num}: Использован артикул '{component_sku}' как наименование.")
        
        try:
            quantity_str = str(qty_val).replace(',', '.').strip() if qty_val is not None else '0'
            quantity = Decimal(quantity_str)
            if quantity <= Decimal('0'):
                warnings.append(f"Строка {row_num}: Кол-во '{qty_val}' для '{component_name or component_sku}' <= 0. Компонент пропущен.")
                continue
        except InvalidOperation:
            errors.append(f"Строка {row_num}: Некорректное кол-во '{qty_val}' для '{component_name or component_sku}'. Компонент пропущен.")
            continue
        
        unit = str(unit_val).strip() if unit_val is not None else None
        if not unit:
            errors.append(f"Строка {row_num}: Отсутствует ед.изм. для '{component_name or component_sku}'. Компонент пропущен.")
            continue

        component_data['num'] = len(parsed_components) + 1
        component_data['Артикул'] = component_sku
        component_data['Наименование материала'] = component_name
        component_data['Количество'] = quantity
        component_data['Единица измерения'] = unit

        if price_val is not None and col_map.get("price_optional"):
            try:
                price_str = str(price_val).replace(',', '.').strip()
                excel_price = Decimal(price_str)
                if excel_price < Decimal('0'):
                    warnings.append(f"Строка {row_num}: Отрицательная цена из Excel '{price_val}' для '{component_name or component_sku}'. Цена проигнорирована.")
                else:
                    component_data['Цена из Excel'] = excel_price
            except InvalidOperation:
                warnings.append(f"Строка {row_num}: Некорректная цена из Excel '{price_val}' для '{component_name or component_sku}'. Цена проигнорирована.")
        
        parsed_components.append(component_data)

    if not parsed_components and not errors:
        warnings.append("Компоненты в файле не найдены или все были отфильтрованы.")
        
    return {
        'product_sku': product_sku,
        'tech_card_name': tech_card_name,
        'tech_card_version': tech_card_version,
        'components': parsed_components,
        'errors': errors,
        'warnings': warnings
    }

if __name__ == '__main__':
    logger.setLevel(logging.DEBUG) 
    test_file_dir = "test_excel_files_parser" # Отдельная папка для тестов парсера
    os.makedirs(test_file_dir, exist_ok=True)
    
    test_file1 = os.path.join(test_file_dir, 'test_techcard_std.xlsx')
    # ... (код для создания test_file1 и test_file2 как в предыдущем вашем примере) ...
    # ... (я его здесь опускаю для краткости, но он должен быть здесь для локального теста) ...

    # Пример создания тестового файла (упрощенный, добавьте больше строк как в вашем коде)
    if not os.path.exists(test_file1):
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Компоненты"
            ws['A1'] = "Артикул"
            ws['B1'] = "Наименование материала"
            ws['C1'] = "Количество"
            ws['D1'] = "Ед.изм."
            ws['A2'] = "SKU001"; ws['B2'] = "ЛДСП (16мм)"; ws['C2'] = 2.5; ws['D2'] = "м2"
            ws['A3'] = "SKU002"; ws['B3'] = "Кромка ПВХ"; ws['C3'] = 10; ws['D3'] = "м.п."
            wb.save(test_file1)
            logger.info(f"Создан тестовый файл: {test_file1}")
        except Exception as e:
            logger.error(f"Не удалось создать {test_file1}: {e}")


    def run_test(file_path, sku_hint=None, name_hint=None, version_hint=None, temp_metadata_cells=None):
        # ... (код функции run_test как в предыдущем вашем примере) ...
        global METADATA_CELLS 
        original_meta_cells_backup = METADATA_CELLS.copy()
        if temp_metadata_cells:
            METADATA_CELLS = temp_metadata_cells
        
        logger.info(f"\n--- Тестирование парсера с файлом: {file_path} ---")
        logger.info(f"Подсказки: SKU='{sku_hint}', Имя='{name_hint}', Версия='{version_hint}'")
        logger.info(f"Используемые METADATA_CELLS: {METADATA_CELLS}")

        data = parse_excel_data(file_path, product_sku_hint=sku_hint, tech_card_name_hint=name_hint, tech_card_version_hint=version_hint)
        if data:
            logger.info("\n--- Результат парсинга ---")
            logger.info(f"SKU Продукта: {data.get('product_sku')}")
            logger.info(f"Имя Техкарты: {data.get('tech_card_name')}")
            logger.info(f"Версия: {data.get('tech_card_version')}")
            
            if data.get('errors'):
                logger.error("Ошибки парсинга:")
                for err in data['errors']: logger.error(f"  - {err}")
            if data.get('warnings'):
                logger.warning("Предупреждения парсинга:")
                for warn in data['warnings']: logger.warning(f"  - {warn}")

            logger.info("Компоненты:")
            if data.get('components'):
                for comp in data.get('components', []):
                    price_info = f", ЦенаExcel: {comp.get('Цена из Excel')}" if 'Цена из Excel' in comp else ""
                    logger.info(f"  {comp.get('num')}. Арт: {comp.get('Артикул')}, "
                                f"Имя: {comp.get('Наименование материала')}, "
                                f"Кол-во: {comp.get('Количество')} ({type(comp.get('Количество'))}), "
                                f"Ед: {comp.get('Единица измерения')}{price_info}")
            else:
                logger.info("  Компоненты не найдены или не были распарсены.")
        else:
            logger.error("Парсинг не вернул данных (возможно, критическая ошибка при открытии файла).")
        
        METADATA_CELLS = original_meta_cells_backup 
        logger.info("--- Тестирование завершено ---")


    if os.path.exists(test_file1):
        run_test(test_file1, sku_hint="PROD-HINT-001", name_hint="Подсказка имени ТК", version_hint="vHint")
    else:
        logger.error(f"Тестовый файл {test_file1} не найден.")
    
    # Добавьте здесь создание и тест для test_file2, если нужно, как в вашем примере
    # ...

    run_test("non_existent_file.xlsx") # Тест с несуществующим файлом
