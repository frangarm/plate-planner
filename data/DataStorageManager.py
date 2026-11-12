import json
import sqlite3
from contextlib import contextmanager, nullcontext
 
RECORD_TYPE_RECIPE = "recipe"
RECORD_TYPE_MEAL_PLAN = "meal_plan"
RECORD_TYPE_GROCERY_LIST = "grocery_list"
RECORD_TYPES = frozenset({RECORD_TYPE_RECIPE, RECORD_TYPE_MEAL_PLAN, RECORD_TYPE_GROCERY_LIST})

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
    
    @contextmanager
    def write_transaction(self):
        """Serialize a read followed by a write across database connections."""
        try:
            with self._db:
                self._db.execute("BEGIN IMMEDIATE")
                yield
        except sqlite3.Error as error:
            raise StorageError("Could not complete the database transaction.") from error

    #Helper functions, will check the record type, data, and id of incoming store requests 
    @staticmethod
    def check_record_type(record_type: str) -> None:
        """Raise ValueError if record_type is not a known record type."""
        if record_type not in RECORD_TYPES:
            raise ValueError(f"record_type must be one of {sorted(RECORD_TYPES)}")

    @staticmethod
    def check_record_data(record_data: dict) -> None:
        """Raise TypeError if record_data is not a dict."""
        if not isinstance(record_data, dict):
            raise TypeError("record_data must be a dict")
    
    @staticmethod
    def check_record_id(record_id: int) -> None:
        """Raise ValueError if record_id is not a whole number of 1 or more."""
        if not isinstance(record_id, int) or isinstance(record_id, bool) or record_id < 1:
            raise ValueError("record_id must be a whole number greater than 0")


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
        
        self.check_record_type(record_type)
        self.check_record_data(record_data)
        
        if not self.validate_relationships(record_type, record_data):
            return None

        try:
            with self._db:
                row = self._db.execute(
                    "SELECT last_id FROM id_counters WHERE record_type = ?",
                    (record_type,)).fetchone()
                record_id = (row[0] if row else 0) + 1
                self._db.execute(
                    "INSERT OR REPLACE INTO id_counters VALUES (?, ?)", (record_type, record_id))
                self._db.execute(
                    "INSERT INTO records VALUES (?, ?, ?)",
                    (record_type, record_id, json.dumps(record_data)))
        except sqlite3.Error as error:
            raise StorageError(f"cannot save {record_type}: {error}") from error
        return record_id

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
        self.check_record_type(record_type)
        self.check_record_id(record_id)
        self.check_record_data(record_data)
        
        if self.get_record(record_type, record_id) is None:
            return False
        
        if not self.validate_relationships(record_type, record_data):
            return False
        
        try:
            transaction = nullcontext() if self._db.in_transaction else self._db
            with transaction:
                self._db.execute(
                    "UPDATE records SET data = ? WHERE record_type = ? AND record_id = ?",
                    (json.dumps(record_data), record_type, record_id))
        except sqlite3.Error as error:
            raise StorageError(f"cannot update {record_type} {record_id}: {error}") from error
        return True

    
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
        self.check_record_type(record_type)
        self.check_record_id(record_id)
        with self.write_transaction():
            if self.get_record(record_type, record_id) is None:
                return False

            if record_type == RECORD_TYPE_RECIPE and self.is_used_by_a_meal_plan(record_id):
                return False

            self._db.execute(
                "DELETE FROM records WHERE record_type = ? AND record_id = ?",
                (record_type, record_id),
            )
        return True

    #Helper function that checks if a recipe is used by a meal plan
    def is_used_by_a_meal_plan(self, recipe_id: int) -> bool:
        
        return any(meal.get("recipe_id") == recipe_id for plan in self.get_all_records(RECORD_TYPE_MEAL_PLAN) for meal in plan.get("meals", []))

    
    """
        Pre-conditions: 

            @requires record_type in {"recipe", "meal_plan", "grocery_list"} 
            @requires record_data != None 
            @requires type(record_data) == dict 

    Post-conditions: 

            @ensures \result == True iff all required record references are valid 
            @ensures \result == False iff at least one required record reference is invalid 
            @ensures database remains unchanged 
    """
    def validate_relationships(self, record_type: str, record_data: dict) -> bool:
        self.check_record_type(record_type)
        self.check_record_data(record_data)
        if record_type != RECORD_TYPE_MEAL_PLAN:
            return True
        return all(self.recipe_is_saved(meal.get("recipe_id")) for meal in record_data.get("meals", []))

    #Helper that checks whether a recipe with the given ID is saved
    def recipe_is_saved(self, recipe_id: object) -> bool:
        if not isinstance(recipe_id, int) or isinstance(recipe_id, bool) or recipe_id < 1:
            return False
        return self.get_record(RECORD_TYPE_RECIPE, recipe_id) is not None

    """
        Pre-conditions: 

            @requires record_type in {"recipe", "meal_plan", "grocery_list"} 
            @requires record_id > 0 

        Post-conditions: 

            @ensures record_id exists => \result contains requested record 
            @ensures record_id does not exist => \result == None 
    """
    def get_record(self, record_type: str, record_id: int) -> dict | None: 
        self.check_record_type(record_type)
        self.check_record_id(record_id)
        try:
            row = self._db.execute(
                "SELECT data FROM records WHERE record_type = ? AND record_id = ?",
                (record_type, record_id)).fetchone()
        except sqlite3.Error as error:
            raise StorageError(f"cannot read {record_type} {record_id}: {error}") from error
        if row is None:
            return None
        return {**json.loads(row[0]), "record_id": record_id}

    
    """
        Pre-conditions: 

            @requires record_type in {"recipe", "meal_plan", "grocery_list"} 
        
        Post-conditions:
            @ensures \result contains all saved records of record_type 
            @ensures no records exist => \result == [] 
    """
    def get_all_records(self, record_type: str) -> list[dict]: 
        self.check_record_type(record_type)
        try:
            rows = self._db.execute(
                "SELECT record_id, data FROM records WHERE record_type = ? ORDER BY record_id",
                (record_type,)).fetchall()
        except sqlite3.Error as error:
            raise StorageError(f"cannot read {record_type} records: {error}") from error
        return [{**json.loads(data), "record_id": record_id} for record_id, data in rows]
