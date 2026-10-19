import requests
from database import get_db

API_URL = "https://dummyjson.com/products?limit=0"

print("=" * 40)
print("STARTING PRODUCT IMPORT")
print("=" * 40)

try:
    # Database connection
    db = get_db()
    cursor = db.cursor()

    print("MySQL connected successfully")

    # API se products fetch karo
    print("Fetching products from API...")
    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()

    data = response.json()
    products = data.get("products", [])

    print(f"Total products received: {len(products)}")

    # Existing products delete karo
    cursor.execute("DELETE FROM products")
    db.commit()

    print("Old products cleared")

    successful = 0
    failed = 0

    # Products insert karo
    for product in products:
        try:
            name = product.get("title", "")
            description = product.get("description", "")
            price = product.get("price", 0)
            category = product.get("category", "")

            sql = """
                INSERT INTO products
                (name, description, price, category)
                VALUES (%s, %s, %s, %s)
            """

            values = (
                name,
                description,
                price,
                category
            )

            cursor.execute(sql, values)

            successful += 1

        except Exception as e:
            failed += 1
            print(f"Failed product: {product.get('title')}")
            print("Error:", e)

    # Changes save
    db.commit()

    print()
    print("=" * 40)
    print("PRODUCT IMPORT COMPLETE")
    print("=" * 40)
    print(f"Total API products : {len(products)}")
    print(f"Successfully added : {successful}")
    print(f"Failed             : {failed}")

    cursor.close()
    db.close()

except Exception as e:
    print()
    print("IMPORT ERROR:", repr(e))