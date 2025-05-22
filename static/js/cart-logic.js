// js/cart-logic.js

// --- ОБЩИЙ МАССИВ ТОВАРОВ (МОК) ---
const allMockProductsForCart = [
    { id: 1, name: 'Тумба "Modern" 75см', sku: 'WS-MOD75-ANT', category: { name: "Тумбы с раковиной", slug: "tumbi" }, price: 28500, oldPrice: 32000, availability: 'В наличии', weightKg: 25.5, volumeM3: 0.15, images: ['https://placehold.co/600x500/e0f2fe/0c4a6e?text=Тумба+Modern+Вид+1', 'https://placehold.co/600x500/c7d2fe/3730a3?text=Тумба+Modern+Вид+2', 'https://placehold.co/600x500/ddd6fe/5b21b6?text=Тумба+Modern+Вид+3'], keyFeatures: [{ name: "Ширина", value: "750 мм" }, { name: "Высота", value: "520 мм" }, { name: "Цвет", value: "Антрацит" }, { name: "Вес", value: "25.5 кг" }], shortDescription: ["Современный дизайн", "Влагостойкие материалы", "2 ящика"], fullDescription: "<p>Полное описание тумбы Modern 75см...</p>", specifications: [{ name: "Ширина", value: "75 см" }], reviews: [{ author: "Елена", rating: 5, text: "Отлично!" }] },
    { id: 2, name: 'Зеркало "Orion" с LED', sku: 'WS-ZER-ORL', category: { name: "Зеркала", slug: "zerkala" }, price: 12900, oldPrice: null, availability: 'В наличии', weightKg: 8.0, volumeM3: 0.05, images: ['https://placehold.co/600x500/fef9c3/713f12?text=Зеркало+Orion+LED'], keyFeatures: [{ name: "Размер", value: "80x60 см" }, { name: "Подсветка", value: "LED" }, { name: "Вес", value: "8 кг" }], shortDescription: ["Сенсорное включение", "Яркая подсветка"], fullDescription: "<p>Описание зеркала Orion...</p>", specifications: [{ name: "Размер", value: "80x60 см" }], reviews: [] },
    { id: 3, name: 'Пенал "Linea Slim"', sku: 'WS-PEN-LIN', category: { name: "Пеналы", slug: "penali" }, price: 17300, oldPrice: 18500, availability: 'Под заказ (7 дней)', weightKg: 15.2, volumeM3: 0.1, images: ['https://placehold.co/600x500/ecfccb/365314?text=Пенал+Linea+Slim'], keyFeatures: [{ name: "Высота", value: "150 см" }, { name: "Цвет", value: "Дуб крафт" }, { name: "Вес", value: "15.2 кг" }], shortDescription: ["Подвесной", "Компактный"], fullDescription: "<p>Описание пенала Linea Slim...</p>", specifications: [{ name: "Высота", value: "150 см" }], reviews: [] },
    { id: 4, name: 'Тумба "Classic" 90см', sku: 'WS-CLA90-WHT', category: { name: "Тумбы с раковиной", slug: "tumbi" }, price: 32000, oldPrice: null, availability: 'В наличии', weightKg: 28.0, volumeM3: 0.18, images: ['https://placehold.co/600x500/fee2e2/9f1239?text=Тумба+Classic+90'], keyFeatures: [], shortDescription: [], fullDescription: "", specifications: [], reviews: [] },
    { id: 5, name: 'Шкаф зеркальный "Comfort"', sku: 'WS-ZER-COM', category: { name: "Зеркала", slug: "zerkala" }, price: 18900, oldPrice: 21000, availability: 'В наличии', weightKg: 12.5, volumeM3: 0.08, images: ['https://placehold.co/600x500/dcfce7/166534?text=Зеркальный+шкаф+Comfort'], keyFeatures: [], shortDescription: [], fullDescription: "", specifications: [], reviews: [] },
    { id: 6, name: 'Комплект "Elegance"', sku: 'WS-SET-ELE', category: { name: "Комплекты мебели", slug: "komplekti" }, price: 55700, oldPrice: null, availability: 'Под заказ (10 дней)', weightKg: 45.0, volumeM3: 0.3, images: ['https://placehold.co/600x500/e0e7ff/3730a3?text=Комплект+Elegance'], keyFeatures: [], shortDescription: [], fullDescription: "", specifications: [], reviews: [] },
    { id: 7, name: 'Тумба "Minimal" 60см', sku: 'WS-MIN60-GR', category: { name: "Тумбы с раковиной", slug: "tumbi" }, price: 22500, oldPrice: null, availability: 'В наличии', weightKg: 20.0, volumeM3: 0.12, images: ['https://placehold.co/600x500/6b7280/e5e7eb?text=Тумба+Minimal+60'], keyFeatures: [], shortDescription: [], fullDescription: "", specifications: [], reviews: [] },
    { id: 8, name: 'Зеркало "Aura" круглое', sku: 'WS-ZER-AUR', category: { name: "Зеркала", slug: "zerkala" }, price: 8500, oldPrice: null, availability: 'В наличии', weightKg: 5.0, volumeM3: 0.03, images: ['https://placehold.co/600x500/9ca3af/f3f4f6?text=Зеркало+Aura'], keyFeatures: [], shortDescription: [], fullDescription: "", specifications: [], reviews: [] },
    { id: 9, name: 'Аксессуар "Мыльница Stone"', sku: 'WS-ACC-STN', category: { name: "Аксессуары", slug: "aksesuari" }, price: 1200, oldPrice: null, availability: 'В наличии', weightKg: 0.5, volumeM3: 0.005, images: ['https://placehold.co/400x300/a1a1aa/f4f4f5?text=Мыльница+Stone'], keyFeatures: [], shortDescription: [], fullDescription: "", specifications: [], reviews: [] },
    { id: 10, name: 'Тумба "Woodline" 80см', sku: 'WS-WDL80-OAK', category: { name: "Тумбы с раковиной", slug: "tumbi" }, price: 42000, oldPrice: null, availability: 'Под заказ (14 дней)', weightKg: 30.0, volumeM3: 0.2, images: ['https://placehold.co/400x300/d2b48c/f5f5dc?text=Тумба+Woodline'], keyFeatures: [], shortDescription: [], fullDescription: "", specifications: [], reviews: [] },
];

function getCart() {
    const cart = localStorage.getItem('shoppingCart');
    return cart ? JSON.parse(cart) : [];
}

function saveCart(cartData) {
    console.log("Сохранение корзины:", cartData); // DEBUG
    localStorage.setItem('shoppingCart', JSON.stringify(cartData));
    updateCartCountersOnAllPages();
}

function addToCart(productId, quantity = 1) {
    console.log(`Попытка добавить в корзину: ID товара ${productId}, Количество ${quantity}`); // DEBUG
    let cart = getCart();
    const productInfo = allMockProductsForCart.find(p => p.id === productId);

    if (!productInfo) {
        console.error(`Товар с ID ${productId} не найден в общем списке allMockProductsForCart.`);
        alert("Ошибка: информация о товаре не найдена.");
        return;
    }

    const existingItemIndex = cart.findIndex(item => item.id === productId);

    if (existingItemIndex > -1) {
        cart[existingItemIndex].quantity += quantity;
        console.log(`Количество товара ID ${productId} увеличено до ${cart[existingItemIndex].quantity}`); // DEBUG
    } else {
        cart.push({
            id: productId,
            quantity: quantity,
        });
        console.log(`Товар ID ${productId} добавлен в корзину с количеством ${quantity}`); // DEBUG
    }
    saveCart(cart);
    showToastNotification(`${productInfo.name} добавлен в корзину!`);
}

function updateCartCountersOnAllPages() {
    const cart = getCart();
    const totalItemsInCart = cart.reduce((sum, item) => sum + item.quantity, 0);
    console.log("Обновление счетчиков корзины, всего товаров:", totalItemsInCart); // DEBUG

    const counterIds = [
        'cart-count-desktop', 'cart-count-mobile',
        'cart-count-desktop-detail', 'cart-count-mobile-detail',
        'cart-count-desktop-cart', 'cart-count-mobile-cart',
        'cart-count-desktop-login', 'cart-count-mobile-login',       // Для login.html
        'cart-count-desktop-register', 'cart-count-mobile-register', // Для register.html
        'cart-count-desktop-account', 'cart-count-mobile-account'    // Для account.html (уже было)
    ];

    counterIds.forEach(id => {
        const counterElement = document.getElementById(id);
        if (counterElement) {
            counterElement.textContent = totalItemsInCart;
        }
    });
}

function showToastNotification(message, duration = 3000) {
    let toast = document.getElementById('toast-notification');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast-notification';
        toast.className = 'fixed bottom-5 right-5 bg-green-500 text-white py-3 px-6 rounded-lg shadow-xl text-sm z-[150] transition-opacity duration-300 ease-out opacity-0';
        document.body.appendChild(toast);
    }

    toast.textContent = message;
    // Принудительный reflow для перезапуска анимации, если toast уже видим
    void toast.offsetWidth;

    toast.classList.remove('opacity-0');
    toast.classList.add('opacity-100');

    setTimeout(() => {
        toast.classList.remove('opacity-100');
        toast.classList.add('opacity-0');
    }, duration);
}

document.addEventListener('DOMContentLoaded', () => {
    updateCartCountersOnAllPages();
});
