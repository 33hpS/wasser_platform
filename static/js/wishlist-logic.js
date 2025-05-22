// js/wishlist-logic.js
console.log("wishlist-logic.js загружен");

const WISHLIST_STORAGE_KEY = 'userWishlist';

/**
 * Получает текущий список желаний из localStorage.
 * @returns {Array<number>} Массив ID товаров в списке желаний.
 */
function getWishlist() {
    const wishlist = localStorage.getItem(WISHLIST_STORAGE_KEY);
    return wishlist ? JSON.parse(wishlist) : [];
}

/**
 * Сохраняет список желаний в localStorage.
 * @param {Array<number>} wishlistData Массив ID товаров.
 */
function saveWishlist(wishlistData) {
    localStorage.setItem(WISHLIST_STORAGE_KEY, JSON.stringify(wishlistData));
    // Опционально: обновить UI элементы, связанные со списком желаний на текущей странице, если они есть
    if (typeof updateWishlistButtonsUI === 'function') {
        updateWishlistButtonsUI(); // Предполагается, что такая функция есть на страницах
    }
    // Также можно обновить счетчик желаний, если он будет
}

/**
 * Проверяет, находится ли товар в списке желаний.
 * @param {number} productId ID товара.
 * @returns {boolean} True, если товар в списке, иначе false.
 */
function isProductInWishlist(productId) {
    const wishlist = getWishlist();
    return wishlist.includes(productId);
}

/**
 * Добавляет или удаляет товар из списка желаний.
 * Показывает уведомление.
 * @param {number} productId ID товара.
 */
function toggleWishlist(productId) {
    console.log(`[Wishlist] toggleWishlist для productId: ${productId}`);
    let wishlist = getWishlist();
    const productIndex = wishlist.indexOf(productId);
    let productName = `Товар (ID: ${productId})`; // Имя по умолчанию

    // Пытаемся получить имя товара из allMockProductsForCart (предполагается, что он доступен глобально из cart-logic.js)
    // или из локального allMockProducts, если он есть на странице
    let productSource = [];
    if (typeof allMockProductsForCart !== 'undefined' && Array.isArray(allMockProductsForCart)) {
        productSource = allMockProductsForCart;
    } else if (typeof allMockProducts !== 'undefined' && Array.isArray(allMockProducts)) { // Для product-detail.html
        productSource = allMockProducts;
    }

    const productInfo = productSource.find(p => p.id === productId);
    if (productInfo && productInfo.name) {
        productName = productInfo.name;
    }

    if (productIndex > -1) {
        // Товар уже в списке, удаляем его
        wishlist.splice(productIndex, 1);
        saveWishlist(wishlist);
        console.log(`[Wishlist] Товар "${productName}" удален из списка желаний.`);
        if (typeof showToastNotification === 'function') { // showToastNotification из cart-logic.js
            showToastNotification(`"${productName}" удален из списка желаний`);
        } else {
            alert(`"${productName}" удален из списка желаний`);
        }
    } else {
        // Товара нет в списке, добавляем его
        wishlist.push(productId);
        saveWishlist(wishlist);
        console.log(`[Wishlist] Товар "${productName}" добавлен в список желаний.`);
        if (typeof showToastNotification === 'function') {
            showToastNotification(`"${productName}" добавлен в список желаний!`);
        } else {
            alert(`"${productName}" добавлен в список желаний!`);
        }
    }
    // Обновляем UI на странице личного кабинета, если мы там
    if (document.getElementById('wishlist-items-list') && typeof renderWishlist === 'function') {
        renderWishlist();
    }
}

// Функция для обновления UI кнопок списка желаний (должна быть вызвана на страницах, где есть эти кнопки)
// Пример такой функции может быть определен на каждой странице отдельно или в общем скрипте.
// function updateWishlistButtonsUI() {
//     document.querySelectorAll('.wishlist-toggle-button').forEach(button => {
//         const productId = parseInt(button.dataset.productId);
//         if (isProductInWishlist(productId)) {
//             button.classList.add('active'); // или меняем иконку
//             button.title = 'Удалить из списка желаний';
//         } else {
//             button.classList.remove('active');
//             button.title = 'Добавить в список желаний';
//         }
//     });
// }
