# database.py

import sqlite3
import hashlib
from typing import Optional, List, Dict


class Database:
    def __init__(self, db_path: str = "shop_bot.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # ---------- Таблица orders ----------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                order_type TEXT NOT NULL,
                quantity INTEGER,
                target_username TEXT,
                target_type TEXT,
                price REAL NOT NULL,
                price_usd REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                payment_status TEXT DEFAULT 'unpaid',
                invoice_id INTEGER,
                pay_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                admin_message_id INTEGER,
                user_message_id INTEGER,
                user_chat_id INTEGER,
                note TEXT,
                promocode_id INTEGER,
                discount_amount REAL DEFAULT 0
            )
        """)

        for col_name, col_type in [
            ('promocode_id', 'INTEGER'),
            ('discount_amount', 'REAL DEFAULT 0'),
        ]:
            try:
                cursor.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass

        # ---------- Таблица users ----------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                balance_stars INTEGER DEFAULT 0,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                orders_count INTEGER DEFAULT 0,
                total_spent REAL DEFAULT 0
            )
        """)

        for col_name, col_type in [
            ('referral_code', 'TEXT UNIQUE'),
            ('referred_by', 'INTEGER'),
            ('balance_stars', 'INTEGER DEFAULT 0'),
        ]:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass

        # ---------- Таблица promocodes ----------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                discount_type TEXT CHECK(discount_type IN ('percent', 'fixed')),
                discount_value REAL NOT NULL,
                expires_at TIMESTAMP,
                max_uses INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ---------- Таблица referrals ----------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_rewarded INTEGER DEFAULT 0,
                reward_amount_stars INTEGER DEFAULT 0,
                reward_amount_percent REAL DEFAULT 0
            )
        """)

        # ---------- Таблица emoji_settings ----------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emoji_settings (
                emoji_key TEXT PRIMARY KEY,
                emoji_id TEXT,
                emoji_char TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    # ---------- ПОЛЬЗОВАТЕЛИ ----------
    def add_user(self, user_id: int, username: str, full_name: str, referred_by: int = None):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT user_id, referral_code FROM users WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE users SET username = ?, full_name = ?
                WHERE user_id = ?
            """, (username, full_name, user_id))
            conn.commit()
            conn.close()
            return existing['referral_code']

        # Генерируем код БЕЗ префикса ref_
        code_hash = hashlib.md5(str(user_id).encode()).hexdigest()[:8]
        referral_code = code_hash

        cursor.execute("""
            INSERT INTO users (user_id, username, full_name, referral_code, referred_by)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, full_name, referral_code, referred_by))
        conn.commit()
        conn.close()
        return referral_code

    def get_user(self, user_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_by_ref_code(self, code: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE referral_code = ?", (code,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def add_balance_stars(self, user_id: int, stars: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance_stars = balance_stars + ? WHERE user_id = ?", (stars, user_id))
        conn.commit()
        conn.close()

    def get_balance_stars(self, user_id: int) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance_stars FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row['balance_stars'] if row else 0

    def get_all_users(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ---------- ЗАКАЗЫ ----------
    def create_order(self, user_id, username, full_name, order_type,
                     quantity, target_username, target_type, price,
                     promocode_id: int = None, discount_amount: float = 0):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO orders (user_id, username, full_name, order_type,
                              quantity, target_username, target_type, price,
                              promocode_id, discount_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, full_name, order_type, quantity,
              target_username, target_type, price, promocode_id, discount_amount))
        order_id = cursor.lastrowid
        cursor.execute("""
            UPDATE users SET orders_count = orders_count + 1,
                           total_spent = total_spent + ?
            WHERE user_id = ?
        """, (price, user_id))
        conn.commit()
        conn.close()
        return order_id

    def update_order_status(self, order_id, status):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, order_id))
        conn.commit()
        conn.close()

    def update_payment(self, order_id, invoice_id, pay_url, price_usd):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE orders SET invoice_id = ?, pay_url = ?, price_usd = ?,
                            payment_status = 'pending'
            WHERE id = ?
        """, (invoice_id, pay_url, price_usd, order_id))
        conn.commit()
        conn.close()

    def update_payment_status(self, order_id, status):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE orders SET payment_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, order_id))
        conn.commit()
        conn.close()

    def set_admin_message_id(self, order_id, message_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET admin_message_id = ? WHERE id = ?", (message_id, order_id))
        conn.commit()
        conn.close()

    def set_user_message_id(self, order_id, message_id, chat_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET user_message_id = ?, user_chat_id = ? WHERE id = ?",
                       (message_id, chat_id, order_id))
        conn.commit()
        conn.close()

    def get_order(self, order_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_orders(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM orders WHERE user_id = ?
            ORDER BY created_at DESC LIMIT 10
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_unpaid_orders(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM orders
            WHERE payment_status = 'unpaid' AND status = 'pending'
              AND created_at <= datetime('now', '-15 minutes')
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_stats(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM orders")
        total_orders = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM orders WHERE status='completed'")
        completed = cursor.fetchone()['total']
        cursor.execute("SELECT COALESCE(SUM(price),0) as total FROM orders WHERE status='completed'")
        total_revenue = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(DISTINCT user_id) as total FROM users")
        total_users = cursor.fetchone()['total']
        conn.close()
        return {
            'total_orders': total_orders,
            'completed_orders': completed,
            'total_revenue': total_revenue,
            'total_users': total_users
        }

    # ---------- ПРОМОКОДЫ ----------
    def create_promo(self, code: str, discount_type: str, discount_value: float,
                     expires_at: str, max_uses: int, created_by: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO promocodes (code, discount_type, discount_value, expires_at, max_uses, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (code, discount_type, discount_value, expires_at, max_uses, created_by))
        conn.commit()
        conn.close()

    def get_promo(self, code: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM promocodes WHERE code = ?", (code,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def use_promo(self, code: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?", (code,))
        conn.commit()
        conn.close()

    def list_promos(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM promocodes ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def delete_promo(self, code: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM promocodes WHERE code = ?", (code,))
        conn.commit()
        conn.close()

    # ---------- РЕФЕРАЛЫ ----------
    def save_referral(self, referrer_id: int, referred_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO referrals (referrer_id, referred_id)
            VALUES (?, ?)
        """, (referrer_id, referred_id))
        conn.commit()
        conn.close()

    def get_referral(self, referrer_id: int, referred_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM referrals WHERE referrer_id = ? AND referred_id = ?",
                       (referrer_id, referred_id))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def mark_referral_rewarded(self, referral_id: int, reward_stars: int, reward_percent: float):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE referrals SET is_rewarded = 1,
                                reward_amount_stars = ?,
                                reward_amount_percent = ?
            WHERE id = ?
        """, (reward_stars, reward_percent, referral_id))
        conn.commit()
        conn.close()

    def get_referrals_by_referrer(self, referrer_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM referrals WHERE referrer_id = ?
            ORDER BY created_at DESC
        """, (referrer_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ---------- ЭМОДЗИ ----------
    def set_emoji(self, key, emoji_id, emoji_char):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO emoji_settings (emoji_key, emoji_id, emoji_char, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (key, emoji_id, emoji_char))
        conn.commit()
        conn.close()

    def get_all_emojis(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT emoji_key, emoji_id, emoji_char FROM emoji_settings")
        rows = cursor.fetchall()
        conn.close()
        return {row['emoji_key']: {'id': row['emoji_id'], 'char': row['emoji_char']} for row in rows}

    def clear_emojis(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM emoji_settings")
        conn.commit()
        conn.close()