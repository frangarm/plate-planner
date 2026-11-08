import json
import sqlite3

class StorageError(Exception):
    """The database could not be opened or used."""

class DataStorageManager:
    
    def __init__(self, db_path: str = ":memory:") -> None:
        """Open the database, creating its tables if they do not exist.
 
        Args:
            db_path: Path of the database file, or ":memory:" for a temporary database.
 
        Raises:
            StorageError: If the database cannot be opened.
        """
        try:
            self._db = sqlite3.connect(db_path)
            with self._db:
                self._db.execute(
                    "CREATE TABLE IF NOT EXISTS records ("
                    " record_type TEXT NOT NULL,"
                    " record_id INTEGER NOT NULL,"
                    " data TEXT NOT NULL,"
                    " PRIMARY KEY (record_type, record_id))")
                self._db.execute(
                    "CREATE TABLE IF NOT EXISTS id_counters ("
                    " record_type TEXT PRIMARY KEY,"
                    " last_id INTEGER NOT NULL)")
        except sqlite3.Error as error:
            raise StorageError(f"cannot open database '{db_path}': {error}") from error
 
    def close(self) -> None:
        """Close the database connection."""
        self._db.close()
    
    """
        Pre-conditions: 

                @requires record_type in {"recipe", "meal_plan", "grocery_list"} 
                @requires record_data != None 
                @requires type(record_data) == dict 
                @requires record_data contains valid information 
        
        Post-conditions: 

            @ensures \result != None => new record is stored and result == new record ID 
            @ensures \result == None => no record is added 
    """
    def save_record(self, record_type: str, record_data: dict) -> int | None:
        raise NotImplementedError
    """
    Pre-conditions: 
    
        @requires record_type in {"recipe", "meal_plan", "grocery_list"} 
        @requires record_id > 0 
        @requires record_id exists 
        @requires record_data != None 
        @requires record_data contains valid information 
    
    Post-conditions:
     
        @ensures \result == True => record_id contains updated information 
        @ensures \result == False => existing record remains unchanged 
    """
    def update_record(self, record_type: str, record_id: int, record_data: dict) -> bool:
        raise NotImplementedError
    
    """
    Pre-conditions: 
        @requires record_type in {"recipe", "meal_plan", "grocery_list"} 
        @requires record_id > 0 
        @requires record_id exists
    
    Post-conditions:
        @ensures \result == True => record_id no longer exists 
        @ensures \result == False => existing record remains unchanged 
    """
    def delete_record(self, record_type: str, record_id: int) -> bool: 
        raise NotImplementedError
