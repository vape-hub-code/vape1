import telebot
from telebot.types import WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
import json
import os
import time
from flask import Flask, send_from_directory, jsonify, request
import threading

# ============================================================
#  🔴 ЗАМЕНИ ЭТОТ ТОКЕН НА СВОЙ (получил у @BotFather)
# ============================================================
TOKEN = 'YOUR_TOKEN_HERE'  # Вставь сюда свой токен!

# Пароль для входа в админку (можешь поменять)
ADMIN_PASSWORD = 'admin123'
# ============================================================

bot = telebot.TeleBot(TOKEN)

# Создаём папки для данных
if not os.path.exists('data'):
    os.makedirs('data')
if not os.path.exists('web_app'):
    os.makedirs('web_app')

# Файлы для хранения
PRODUCTS_FILE = 'data/products.json'
ORDERS_FILE = 'data/orders.json'

# ========== ТОВАРЫ (начальные) ==========
def load_products():
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    # Начальные товары (можно потом изменить в админке)
    return {
        "pods": [
            {"id": 1, "name": "HQD Cuvie Plus", "price": 25, "description": "1500 затяжек, компактный", "image": "https://i.imgur.com/placeholder.jpg", "in_stock": True},
            {"id": 2, "name": "Elf Bar 5000", "price": 35, "description": "5000 затяжек, аккумулятор", "image": "https://i.imgur.com/placeholder.jpg", "in_stock": True}
        ],
        "liquids": [
            {"id": 3, "name": "Nasty Juice", "price": 15, "description": "Премиум жидкость 30ml", "image": "https://i.imgur.com/placeholder.jpg", "in_stock": True}
        ]
    }

def save_products(products):
    with open(PRODUCTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

# ========== ЗАКАЗЫ ==========
def save_order(order):
    orders = []
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            orders = json.load(f)
    orders.append(order)
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

# ========== ВЕБ-СЕРВЕР ДЛЯ САЙТА ==========
app = Flask(__name__, static_folder='web_app')

@app.route('/')
def index():
    return send_from_directory('web_app', 'index.html')

@app.route('/admin')
def admin():
    return send_from_directory('web_app', 'admin.html')

@app.route('/api/products')
def api_products():
    return jsonify(load_products())

@app.route('/api/save_products', methods=['POST'])
def api_save_products():
    password = request.headers.get('X-Password')
    if password != ADMIN_PASSWORD:
        return jsonify({'error': 'Wrong password'}), 403
    save_products(request.json)
    return jsonify({'success': True})

def run_server():
    app.run(host='0.0.0.0', port=8080, debug=False)

# ========== КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start'])
def start(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    btn_shop = KeyboardButton('🛍️ МАГАЗИН', web_app=WebAppInfo(url='http://127.0.0.1:8080'))
    btn_admin = KeyboardButton('👑 АДМИН', web_app=WebAppInfo(url='http://127.0.0.1:8080/admin'))
    btn_orders = KeyboardButton('📋 ЗАКАЗЫ')
    btn_contacts = KeyboardButton('📞 КОНТАКТЫ')
    markup.add(btn_shop)
    markup.add(btn_admin, btn_orders)
    markup.add(btn_contacts)
    
    bot.send_message(message.chat.id, 
        f"🌟 Добро пожаловать, {message.from_user.first_name}!\n\n"
        f"🛍️ Нажми 'МАГАЗИН' для покупок\n"
        f"👑 Нажми 'АДМИН' для управления товарами\n"
        f"Пароль админа: {ADMIN_PASSWORD}", 
        reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '📞 КОНТАКТЫ')
def contacts(m):
    bot.send_message(m.chat.id, "📞 +7 (999) 123-45-67\n📧 shop@vape.com\n⏰ 10:00-21:00")

@bot.message_handler(func=lambda m: m.text == '📋 ЗАКАЗЫ')
def orders_list(m):
    if not os.path.exists(ORDERS_FILE):
        bot.send_message(m.chat.id, "У вас нет заказов")
        return
    with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
        orders = json.load(f)
    user_orders = [o for o in orders if o.get('user_id') == m.from_user.id]
    if not user_orders:
        bot.send_message(m.chat.id, "📭 У вас нет заказов")
        return
    for order in user_orders[-3:]:
        text = f"✅ Заказ #{order['order_id']}\n💰 Сумма: ${order['total']}\n📅 {order['date']}"
        bot.send_message(m.chat.id, text)

@bot.message_handler(content_types=['web_app_data'])
def handle_order(m):
    data = json.loads(m.web_app_data.data)
    if data.get('action') == 'checkout':
        order = {
            'order_id': int(time.time()),
            'user_id': m.from_user.id,
            'user_name': m.from_user.first_name,
            'items': data['cart'],
            'total': data['total'],
            'date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'new'
        }
        save_order(order)
        bot.send_message(m.chat.id, f"✅ Заказ #{order['order_id']} принят!\nСумма: ${order['total']}\nМенеджер свяжется с вами")

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    # Запускаем веб-сервер в фоне
    threading.Thread(target=run_server, daemon=True).start()
    print("🤖 Бот запущен!")
    print("📱 Сайт: http://127.0.0.1:8080")
    print(f"🔐 Пароль админа: {ADMIN_PASSWORD}")
    bot.infinity_polling()