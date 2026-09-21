import sqlite3
import os
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
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row # To access columns by name
        try:
            yield conn
        finally:
            conn.close()

db = DatabaseConnection()
