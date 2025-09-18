import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()
cursor.execute("DELETE FROM django_migrations WHERE app='users';")
cursor.execute("DELETE FROM django_migrations WHERE app='loan';")
cursor.execute("DELETE FROM django_migrations WHERE app='payment';")
# Add more lines for other apps if needed
conn.commit()
conn.close()
print("Migration history for 'users', 'loan', and 'payment' apps cleared.")
