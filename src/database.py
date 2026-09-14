"""
src/database.py

Creates a sample e-commerce SQLite database with realistic fake data.
Run once: python src/database.py
"""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

# ---------- Config ----------
DB_PATH = Path("data/sample.db")
NUM_CUSTOMERS = 50
NUM_PRODUCTS = 20
NUM_ORDERS = 80

# ---------- Sample data pools (built-in, no extra libraries) ----------
FIRST_NAMES = ["Aarav", "Priya", "Vihaan", "Ananya", "Rohan", "Diya", "Arjun",
               "Saanvi", "Krishna", "Aanya", "Ishaan", "Aditi", "Reyansh",
               "Pihu", "Atharv", "Myra", "Kiaan", "Anika", "Shaurya", "Arya",
               "Rahul", "Sneha", "Aditya", "Tanvi", "Vivaan", "Riya", "Ayaan",
               "Kavya", "Dhruv", "Ira", "Arnav", "Meera", "Aryan", "Tara",
               "Rudra", "Sara", "Yash", "Niharika", "Veer", "Kiara"]

LAST_NAMES = ["Sharma", "Verma", "Patel", "Kumar", "Singh", "Gupta", "Reddy",
              "Iyer", "Nair", "Khan", "Das", "Joshi", "Mehta", "Kapoor",
              "Chopra", "Malhotra", "Bhat", "Rao", "Saxena", "Banerjee"]

CITIES = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata",
          "Pune", "Ahmedabad", "Jaipur", "Lucknow", "Kanpur", "Nagpur",
          "Indore", "Thane"]

PRODUCTS = [
    ("Laptop", "Electronics", 65000),
    ("Wireless Mouse", "Electronics", 1200),
    ("Mechanical Keyboard", "Electronics", 4500),
    ("Monitor", "Electronics", 18000),
    ("USB-C Hub", "Electronics", 2500),
    ("Webcam", "Electronics", 3500),
    ("Headphones", "Electronics", 12000),
    ("Smartphone", "Electronics", 45000),
    ("Tablet", "Electronics", 28000),
    ("Smart Watch", "Electronics", 15000),
    ("Coffee Maker", "Home", 5500),
    ("Air Purifier", "Home", 9500),
    ("Vacuum Cleaner", "Home", 14000),
    ("Toaster", "Home", 2200),
    ("Blender", "Home", 3800),
    ("Standing Desk", "Furniture", 22000),
    ("Office Chair", "Furniture", 16000),
    ("Bookshelf", "Furniture", 8500),
    ("Desk Lamp", "Furniture", 1800),
    ("Notebook Pack", "Stationery", 450),
]

ORDER_STATUSES = ["pending", "shipped", "delivered", "delivered",
                  "delivered", "cancelled"]


def create_database():
    """Create tables and fill them with sample data."""

    # Make sure data folder exists
    DB_PATH.parent.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop old tables (safe re-runs)
    for table in ["order_items", "orders", "products", "customers"]:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")

    # ---------- Create tables ----------
    cursor.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            city TEXT,
            signup_date DATE
        )
    """)

    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            order_date DATE NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # ---------- Insert data ----------
    random.seed(42)  # reproducible results

    # Customers
    customers = []
    for i in range(NUM_CUSTOMERS):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        city = random.choice(CITIES)
        signup = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 700))
        customers.append((name, email, city, signup.date().isoformat()))

    cursor.executemany(
        "INSERT INTO customers (name, email, city, signup_date) VALUES (?, ?, ?, ?)",
        customers
    )

    # Products
    products_data = [(name, cat, price, random.randint(10, 100))
                     for name, cat, price in PRODUCTS]
    cursor.executemany(
        "INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)",
        products_data
    )

    # Orders + order items
    for _ in range(NUM_ORDERS):
        customer_id = random.randint(1, NUM_CUSTOMERS)
        days_ago = random.randint(1, 365)
        order_date = (datetime.now() - timedelta(days=days_ago)).date().isoformat()
        status = random.choice(ORDER_STATUSES)

        # 1-4 different products in each order
        num_items = random.randint(1, 4)
        items = random.sample(range(1, NUM_PRODUCTS + 1), num_items)

        total = 0
        order_items = []
        for product_id in items:
            quantity = random.randint(1, 3)
            price = PRODUCTS[product_id - 1][2]
            total += quantity * price
            order_items.append((product_id, quantity, price))

        cursor.execute(
            "INSERT INTO orders (customer_id, order_date, total_amount, status) "
            "VALUES (?, ?, ?, ?)",
            (customer_id, order_date, total, status)
        )
        order_id = cursor.lastrowid

        for product_id, quantity, price in order_items:
            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, price) "
                "VALUES (?, ?, ?, ?)",
                (order_id, product_id, quantity, price)
            )

    conn.commit()
    conn.close()

    print(f"✅ Database created at {DB_PATH}")
    print(f"   - {NUM_CUSTOMERS} customers")
    print(f"   - {len(PRODUCTS)} products")
    print(f"   - {NUM_ORDERS} orders")


if __name__ == "__main__":
    create_database()