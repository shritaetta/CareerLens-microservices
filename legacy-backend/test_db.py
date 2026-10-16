import sqlite3
import database

database.init_db()
print(database.create_user('test@example.com', 'Test User', 'hash'))
