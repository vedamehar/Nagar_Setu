import sqlite3

def clean_db():
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE complaints SET status = 'Completed'")
    conn.commit()
    conn.close()
    print("Database cleaned. All previous tests marked as Completed.")

if __name__ == "__main__":
    clean_db()
