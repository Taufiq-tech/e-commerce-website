import mysql.connector


def get_db():
    print("Trying MySQL connection...", flush=True)

    connection = mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="taufiq1234",
        database="taufiqdb",
        connection_timeout=5,
        use_pure=True
    )

    print("MySQL connection successful!", flush=True)

    return connection