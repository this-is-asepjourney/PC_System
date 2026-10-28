import sqlite3
import os
import sys
from contextlib import contextmanager
from src.core.config import config
from src.core.logger import logger

class DatabaseConnection:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance
        
    def _init_db(self):
        self.db_path = config.get('database.path', 'data/pc_system.db')
        if not os.path.isabs(self.db_path):
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(os.path.abspath(sys.executable))
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_path = os.path.join(base_dir, self.db_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize tables
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    cpu_usage REAL,
                    ram_usage REAL,
                    disk_usage REAL,
                    network_download REAL,
                    network_upload REAL
                )
            ''')
            
            # Alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    type TEXT,
                    severity TEXT,
                    message TEXT,
                    resolved INTEGER DEFAULT 0
                )
            ''')
            
            # Logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT,
                    source TEXT,
                    message TEXT
                )
            ''')
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row  # To access columns by name
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        try:
            yield conn
        finally:
            conn.close()

    def clean_old_records(self, retention_days: int = 7):
        """Purges metric and log entries older than retention_days to minimize disk usage."""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "DELETE FROM metrics WHERE timestamp < datetime('now', ?)",
                    (f"-{retention_days} days",)
                )
                conn.execute(
                    "DELETE FROM system_logs WHERE timestamp < datetime('now', ?)",
                    (f"-{retention_days} days",)
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to clean old database records: {e}")

db = DatabaseConnection()
