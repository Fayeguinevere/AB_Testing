"""
Database Manager for A/B Testing Application
Handles all database operations including initialization, queries, and data management.
"""

import sqlite3
import csv
import os
from contextlib import contextmanager


class DatabaseManager:
    """Handles all database operations for A/B testing"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = config["database"]
    
    @contextmanager
    def get_connection(self):
        """Thread-safe database connection context manager"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database and import CSV data if tables are empty"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create tables for both ERP and HRM
            for incident_type in ["erp", "hrm", "sb"]:
                # Questions table
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.config[incident_type]["table_questions"]} (
                        id INTEGER PRIMARY KEY,
                        "Index" TEXT,
                        Incident TEXT,
                        Onderwerp TEXT,
                        Toelichting TEXT,
                        GPTo3_antwoorden TEXT,
                        "GPT-5.1_low_antwoorden" TEXT
                    )
                ''')
                
                # Results table
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.config[incident_type]["table_results"]} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question_index TEXT,
                        model_a TEXT,
                        model_b TEXT,
                        gekozen_optie TEXT,
                        incident_nummer INTEGER,
                        onderwerp TEXT,
                        toelichting TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Check if we need to import CSV data
                cursor.execute(f'SELECT COUNT(*) FROM {self.config[incident_type]["table_questions"]}')
                if cursor.fetchone()[0] == 0:
                    self._import_csv_data(cursor, incident_type)
            
            conn.commit()
    
    def _import_csv_data(self, cursor, incident_type):
        """Import questions from CSV file"""
        csv_file = self.config[incident_type]["csv_ready"]
        if os.path.exists(csv_file):
            with open(csv_file, newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    cursor.execute(f'''
                        INSERT INTO {self.config[incident_type]["table_questions"]} 
                        ("Index", Incident, Onderwerp, Toelichting, GPTo3_antwoorden, "GPT-5.1_low_antwoorden")
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (row.get("Index"), row.get("Incident"), row.get("Onderwerp"), 
                          row.get("Toelichting"), row.get("GPTo3_antwoorden"), 
                          row.get("GPT-5.1_low_antwoorden")))
    
    def get_random_question(self, incident_type):
        """Get a random question from the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT * FROM {self.config[incident_type]["table_questions"]} 
                ORDER BY RANDOM() 
                LIMIT 1
            ''')
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def save_result(self, incident_type, question_index, model_a, model_b, 
                   gekozen_optie, incident_nummer, onderwerp, toelichting):
        """Save user's answer and remove the question from pool"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Save result
            cursor.execute(f'''
                INSERT INTO {self.config[incident_type]["table_results"]}
                (question_index, model_a, model_b, gekozen_optie, incident_nummer, onderwerp, toelichting)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (question_index, model_a, model_b, gekozen_optie, incident_nummer, onderwerp, toelichting))
            
            # Remove answered question
            cursor.execute(f'''
                DELETE FROM {self.config[incident_type]["table_questions"]}
                WHERE "Index" = ?
            ''', (question_index,))
            
            conn.commit()
    
    def get_all_results(self, incident_type):
        """Get all results for an incident type"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT * FROM {self.config[incident_type]["table_results"]}
                ORDER BY timestamp DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self):
        """Get statistics for dashboard"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            for incident_type in ["erp", "hrm", "sb"]:
                cursor.execute(f'SELECT COUNT(*) FROM {self.config[incident_type]["table_results"]}')
                stats[f"{incident_type}_count"] = cursor.fetchone()[0]
                
                cursor.execute(f'SELECT COUNT(*) FROM {self.config[incident_type]["table_questions"]}')
                stats[f"{incident_type}_remaining"] = cursor.fetchone()[0]
            
            return stats
    
    def reset_database(self, incident_type):
        """Reset database for specific incident type or all"""
        types_to_reset = ["erp", "hrm", "sb"] if incident_type == "all" else [incident_type]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for itype in types_to_reset:
                # Clear results
                cursor.execute(f'DELETE FROM {self.config[itype]["table_results"]}')
                
                # Clear questions
                cursor.execute(f'DELETE FROM {self.config[itype]["table_questions"]}')
                
                # Re-import from CSV
                self._import_csv_data(cursor, itype)
            
            conn.commit()
