from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from jinja2 import Environment
import random

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Подключение к базе данных
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы продуктов
cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        price FLOAT NOT NULL
    )
''')
conn.commit()

# Создание таблицы заказов
cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        product_id INTEGER,
        quantity INTEGER NOT NULL,
        total_price FLOAT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
''')
conn.commit()

# Удаление всех записей из таблицы заказов
cursor.execute('DELETE FROM orders')
conn.commit()

# Проверка, есть ли уже продукты в таблице
cursor.execute('SELECT * FROM products')
existing_products = cursor.fetchall()

if not existing_products:
    # Добавление начальных продуктов в базу данных
    cursor.execute('''
        INSERT INTO products (name, price) VALUES
        ('Футболка мужская', 1199.99),
        ('Футболка женская', 1099.99),
        ('Брюки мужские', 899.99),
        ('Брюки женские', 799.99)
    ''')
    conn.commit()

# Создание настраиваемого окружения Jinja2
jinja_env = Environment()
jinja_env.filters['round'] = round


# Маршрут для отображения списка продуктов и корзины
@app.route('/')
def index():
    # Получение списка продуктов из базы данных
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()

    # Получение списка товаров в корзине
    cursor.execute(
        'SELECT orders.id, products.name, products.price, orders.quantity, orders.total_price FROM products JOIN orders ON products.id = orders.product_id')
    cart_items = cursor.fetchall()

    # Подсчет итоговой суммы
    total_sum = sum(item[4] for item in cart_items)

    return render_template('index.html', products=products, cart_items=cart_items, total_sum=total_sum)


# Маршрут для добавления продукта в корзину
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form['product_id']
    quantity = int(request.form['quantity'])

    # Проверка, есть ли уже такой товар в корзине
    cursor.execute('SELECT * FROM orders WHERE product_id = ?', (product_id,))
    existing_order = cursor.fetchone()

    if existing_order:
        # Обновление количества и общей стоимости товара в корзине
        new_quantity = existing_order[3] + quantity
        new_total_price = round(existing_order[4] + (quantity * existing_order[2]), 2)

        cursor.execute('UPDATE orders SET quantity = ?, total_price = ? WHERE id = ?',
                       (new_quantity, new_total_price, existing_order[0]))
    else:
        # Проверка, есть ли товар в базе данных
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()

        if product:
            total_price = round(product[2] * quantity, 2)

            # Добавление заказа в базу данных
            cursor.execute('INSERT INTO orders (product_id, quantity, total_price) VALUES (?, ?, ?)',
                           (product_id, quantity, total_price))

    conn.commit()

    return redirect(url_for('index'))


# Маршрут для удаления товара из корзины
@app.route('/remove_from_cart/<int:order_id>', methods=['POST'])
def remove_from_cart(order_id):
    # Удаление товара из базы данных
    cursor.execute('DELETE FROM orders WHERE id = ?', (order_id,))
    conn.commit()

    return redirect(url_for('index'))


# Маршрут для оплаты
@app.route('/checkout')
def checkout():
    # Получение списка товаров в корзине
    cursor.execute(
        'SELECT orders.id, products.name, products.price, orders.quantity, orders.total_price FROM products JOIN orders ON products.id = orders.product_id')
    cart_items = cursor.fetchall()

    # Подсчет итоговой суммы
    total_sum = sum(item[4] for item in cart_items)

    return render_template('checkout.html', cart_items=cart_items, total_sum=total_sum)


# Маршрут для обработки оплаты
@app.route('/payment', methods=['POST'])
def payment():
    name = request.form['name']
    email = request.form['email']
    address = request.form['address']

    # Сохранение деталей заказа в сессии
    session['order_details'] = {
        'name': name,
        'email': email,
        'address': address
    }

    return redirect(url_for('payment_success'))


@app.route('/payment_success')
def payment_success():
    # Получение сохраненных деталей заказа из сессии
    order_details = session.get('order_details')

    if order_details:
        # Генерация случайного номера заказа
        order_number = random.randint(100000, 999999)
        order_details['order_number'] = order_number

        return render_template('payment_success.html', order_details=order_details)
    else:
        # Если детали заказа не найдены, перенаправляем на страницу оформления заказа
        return redirect(url_for('checkout'))


if __name__ == '__main__':
    app.run()
