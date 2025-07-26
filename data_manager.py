# ===== data_manager.py (SQLite version) =====
import pandas as pd
import sqlite3
import os
import json
from datetime import datetime
from contextlib import contextmanager


class DataManager:
    def __init__(self):
        self.data_dir = 'data'
        self.db_path = os.path.join(self.data_dir, 'stocks.db')

        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)

        # Initialize database
        self._initialize_database()

    def _initialize_database(self):
        """Initialize SQLite database with required tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create stocks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    group_name TEXT NOT NULL,
                    company_name TEXT DEFAULT '',
                    added_date TEXT NOT NULL,
                    UNIQUE(stock_code, group_name)
                )
            ''')

            # Create portfolio table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL UNIQUE,
                    quantity REAL NOT NULL,
                    buy_price REAL NOT NULL,
                    added_date TEXT NOT NULL
                )
            ''')

            # Create stock_data table for OHLCV data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    period TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    volume INTEGER,
                    UNIQUE(stock_code, period, date)
                )
            ''')

            # Create fundamental_data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fundamental_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL UNIQUE,
                    data_json TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            ''')

            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_code ON stocks(stock_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_group ON stocks(group_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_data_code_period ON stock_data(stock_code, period)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_data_date ON stock_data(date)')

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()

    def add_stock_to_group(self, stock_code, group):
        """Add a stock to a specific group with improved error handling"""
        try:
            # Ensure stock_code is properly formatted
            stock_code = str(stock_code).strip().upper()
            if not stock_code or stock_code == 'NAN':
                print(f"Invalid stock code: {stock_code}")
                return False

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check if stock already exists in the group
                cursor.execute('''
                    SELECT COUNT(*) FROM stocks 
                    WHERE stock_code = ? AND group_name = ?
                ''', (stock_code, group))

                if cursor.fetchone()[0] > 0:
                    print(f"Stock {stock_code} already exists in group {group}")
                    return False  # Stock already exists

                # Add new stock
                cursor.execute('''
                    INSERT INTO stocks (stock_code, group_name, company_name, added_date)
                    VALUES (?, ?, ?, ?)
                ''', (stock_code, group, '', datetime.now().strftime('%Y-%m-%d')))

                conn.commit()
                print(f"Stock {stock_code} successfully added to {group}")
                return True

        except Exception as e:
            print(f"Error adding stock {stock_code} to group {group}: {e}")
            return False

    def add_stock_to_portfolio(self, stock_code, quantity, buy_price):
        """Add a stock to personal portfolio with quantity and buy price"""
        try:
            # Ensure proper formatting
            stock_code = str(stock_code).strip().upper()
            quantity = float(quantity)
            buy_price = float(buy_price)

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check if stock already exists in portfolio
                cursor.execute('SELECT * FROM portfolio WHERE stock_code = ?', (stock_code,))
                existing = cursor.fetchone()

                if existing:
                    # Update existing record - average the buy price and sum quantities
                    existing_quantity = existing['quantity']
                    existing_buy_price = existing['buy_price']

                    total_quantity = existing_quantity + quantity
                    weighted_avg_price = ((existing_quantity * existing_buy_price) +
                                          (quantity * buy_price)) / total_quantity

                    cursor.execute('''
                        UPDATE portfolio 
                        SET quantity = ?, buy_price = ? 
                        WHERE stock_code = ?
                    ''', (total_quantity, weighted_avg_price, stock_code))
                else:
                    # Add new record
                    cursor.execute('''
                        INSERT INTO portfolio (stock_code, quantity, buy_price, added_date)
                        VALUES (?, ?, ?, ?)
                    ''', (stock_code, quantity, buy_price, datetime.now().strftime('%Y-%m-%d')))

                conn.commit()

                # Also add to main stocks table
                self.add_stock_to_group(stock_code, 'Personal_Portfolio')

                return True
        except Exception as e:
            print(f"Error adding stock to portfolio: {e}")
            return False

    def delete_stock_from_group(self, stock_code, group):
        """Delete a stock from a specific group"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Delete from stocks table
                cursor.execute('''
                    DELETE FROM stocks 
                    WHERE stock_code = ? AND group_name = ?
                ''', (stock_code, group))

                deleted_count = cursor.rowcount

                # If deleting from Personal Portfolio, also delete from portfolio table
                if group == 'Personal_Portfolio':
                    cursor.execute('DELETE FROM portfolio WHERE stock_code = ?', (stock_code,))

                conn.commit()

                if deleted_count > 0:
                    print(f"Successfully deleted {stock_code} from {group}")
                    return True
                else:
                    print(f"Stock {stock_code} not found in group {group}")
                    return False

        except Exception as e:
            print(f"Error deleting stock: {e}")
            return False

    def get_all_stocks(self):
        """Get all stocks grouped by group"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get all stocks with portfolio data
                cursor.execute('''
                    SELECT s.*, p.quantity, p.buy_price, p.added_date as portfolio_added_date
                    FROM stocks s
                    LEFT JOIN portfolio p ON s.stock_code = p.stock_code
                    ORDER BY s.group_name, s.stock_code
                ''')

                rows = cursor.fetchall()
                stocks_by_group = {}

                for row in rows:
                    group = row['group_name']
                    if group not in stocks_by_group:
                        stocks_by_group[group] = []

                    stock_dict = dict(row)
                    stocks_by_group[group].append(stock_dict)

                return stocks_by_group
        except Exception as e:
            print(f"Error getting stocks: {e}")
            return {}

    def get_stocks_by_group(self, group):
        """Get all stocks in a specific group"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if group == 'Personal_Portfolio':
                    # Get stocks with portfolio data
                    cursor.execute('''
                        SELECT s.*, p.quantity, p.buy_price, p.added_date as portfolio_added_date
                        FROM stocks s
                        LEFT JOIN portfolio p ON s.stock_code = p.stock_code
                        WHERE s.group_name = ?
                        ORDER BY s.stock_code
                    ''', (group,))
                else:
                    cursor.execute('''
                        SELECT * FROM stocks 
                        WHERE group_name = ?
                        ORDER BY stock_code
                    ''', (group,))

                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting stocks by group: {e}")
            return []

    def get_all_stock_codes(self):
        """Get all unique stock codes"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT DISTINCT stock_code FROM stocks ORDER BY stock_code')
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting stock codes: {e}")
            return []

    def save_stock_data(self, stock_code, data, period):
        """Save stock OHLCV data"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Clear existing data for this stock and period
                cursor.execute('''
                    DELETE FROM stock_data 
                    WHERE stock_code = ? AND period = ?
                ''', (stock_code, period))

                # Insert new data
                for date, row in data.iterrows():
                    cursor.execute('''
                        INSERT OR REPLACE INTO stock_data 
                        (stock_code, period, date, open_price, high_price, low_price, close_price, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        stock_code,
                        period,
                        date.strftime('%Y-%m-%d'),
                        float(row['Open']),
                        float(row['High']),
                        float(row['Low']),
                        float(row['Close']),
                        int(row['Volume'])
                    ))

                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving stock data: {e}")
            return False

    def get_stock_data(self, stock_code, period='1y'):
        """Get stock OHLCV data"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT date, open_price, high_price, low_price, close_price, volume
                    FROM stock_data 
                    WHERE stock_code = ? AND period = ?
                    ORDER BY date
                ''', (stock_code, period))

                rows = cursor.fetchall()
                if not rows:
                    return pd.DataFrame()

                # Convert to DataFrame
                data = []
                for row in rows:
                    data.append({
                        'Date': row['date'],
                        'Open': row['open_price'],
                        'High': row['high_price'],
                        'Low': row['low_price'],
                        'Close': row['close_price'],
                        'Volume': row['volume']
                    })

                df = pd.DataFrame(data)
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                return df

        except Exception as e:
            print(f"Error getting stock data: {e}")
            return pd.DataFrame()

    def save_fundamental_data(self, stock_code, data):
        """Save fundamental data for a stock"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO fundamental_data 
                    (stock_code, data_json, last_updated)
                    VALUES (?, ?, ?)
                ''', (stock_code, json.dumps(data), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving fundamental data: {e}")
            return False

    def get_fundamental_data(self, stock_code):
        """Get fundamental data for a stock"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT data_json FROM fundamental_data 
                    WHERE stock_code = ?
                ''', (stock_code,))

                row = cursor.fetchone()
                if row:
                    return json.loads(row['data_json'])
                else:
                    return {}
        except Exception as e:
            print(f"Error getting fundamental data: {e}")
            return {}

    def migrate_from_csv(self):
        """Migration helper to import existing CSV data into SQLite"""
        try:
            # Migrate stocks.csv
            stocks_csv = os.path.join(self.data_dir, 'stocks.csv')
            if os.path.exists(stocks_csv):
                df = pd.read_csv(stocks_csv)
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    for _, row in df.iterrows():
                        try:
                            cursor.execute('''
                                INSERT OR IGNORE INTO stocks 
                                (stock_code, group_name, company_name, added_date)
                                VALUES (?, ?, ?, ?)
                            ''', (
                                row.get('stock_code', ''),
                                row.get('group', ''),
                                row.get('company_name', ''),
                                row.get('added_date', datetime.now().strftime('%Y-%m-%d'))
                            ))
                        except Exception as e:
                            print(f"Error migrating stock row: {e}")
                    conn.commit()
                print(f"Migrated {len(df)} stocks from CSV")

            # Migrate portfolio.csv
            portfolio_csv = os.path.join(self.data_dir, 'portfolio.csv')
            if os.path.exists(portfolio_csv):
                df = pd.read_csv(portfolio_csv)
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    for _, row in df.iterrows():
                        try:
                            cursor.execute('''
                                INSERT OR IGNORE INTO portfolio 
                                (stock_code, quantity, buy_price, added_date)
                                VALUES (?, ?, ?, ?)
                            ''', (
                                row.get('stock_code', ''),
                                float(row.get('quantity', 0)),
                                float(row.get('buy_price', 0)),
                                row.get('added_date', datetime.now().strftime('%Y-%m-%d'))
                            ))
                        except Exception as e:
                            print(f"Error migrating portfolio row: {e}")
                    conn.commit()
                print(f"Migrated {len(df)} portfolio entries from CSV")

            # Migrate individual stock data files
            for filename in os.listdir(self.data_dir):
                if filename.endswith('.csv') and '_' in filename and filename not in ['stocks.csv', 'portfolio.csv']:
                    try:
                        parts = filename.replace('.csv', '').split('_')
                        if len(parts) >= 2:
                            stock_code = '_'.join(parts[:-1])  # Handle stock codes with underscores
                            period = parts[-1]

                            filepath = os.path.join(self.data_dir, filename)
                            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
                            self.save_stock_data(stock_code, df, period)
                            print(f"Migrated data for {stock_code} ({period})")
                    except Exception as e:
                        print(f"Error migrating {filename}: {e}")

            # Migrate fundamental data JSON files
            for filename in os.listdir(self.data_dir):
                if filename.endswith('_fundamental.json'):
                    try:
                        stock_code = filename.replace('_fundamental.json', '')
                        filepath = os.path.join(self.data_dir, filename)
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                        self.save_fundamental_data(stock_code, data)
                        print(f"Migrated fundamental data for {stock_code}")
                    except Exception as e:
                        print(f"Error migrating fundamental data for {filename}: {e}")

            print("Migration completed successfully!")
            return True

        except Exception as e:
            print(f"Error during migration: {e}")
            return False