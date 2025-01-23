
import sqlite3
import datetime
from imutils.video import VideoStream
from pyzbar import pyzbar
import imutils
import time
import cv2
import argparse

# 1. Функция для создания подключения к БД
def create_database_connection(db_name):
    """Создает и возвращает подключение к базе данных."""
    try:
      conn = sqlite3.connect(db_name)
      return conn
    except sqlite3.Error as e:
      print(f"Error connecting to database: {e}")
      return None

# 2. Функция для создания таблиц
def create_database_tables(conn):
    """Создает таблицы в базе данных, если они не существуют."""
    if conn is None:
      print("No connection provided for creating tables")
      return
    cursor = conn.cursor()

    try:
      cursor.execute("""
        CREATE TABLE IF NOT EXISTS User (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT,
            password TEXT
        );
      """)

      cursor.execute("""
          CREATE TABLE IF NOT EXISTS Item (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT,
              type_id INTEGER,
              date TEXT,
              FOREIGN KEY (type_id) REFERENCES Type (id)
          );
        """)

      cursor.execute("""
          CREATE TABLE IF NOT EXISTS Type (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT
          );
      """)
      conn.commit()
      print("Tables created successfully")
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")

# 3. Функция для заполнения таблицы Type
def populate_type_table(conn):
    """Заполняет таблицу Type начальными данными, если она пуста."""
    if conn is None:
      print("No connection to populate Type table")
      return
    cursor = conn.cursor()
    try:
      cursor.execute("SELECT COUNT(*) FROM Type")
      count = cursor.fetchone()[0]
      if count == 0:
        types_to_insert = [
            (1, "Milk product"),
            (2, "Bakeries"),
            (3, "Household")
        ]
        for item_id, item_name in types_to_insert:
            cursor.execute(
                "INSERT OR IGNORE INTO Type (id, name) VALUES (?, ?)",
                (item_id, item_name)
            )
        conn.commit()
        print("Type table populated.")
      else:
        print("Type table already populated.")

    except sqlite3.Error as e:
      print(f"Error populating type table: {e}")

# 4. Функция для разбора данных QR-кода
def parse_qr_data(qr_data):
    """Разбирает данные QR-кода в формате CSV."""
    print("Parsing QR data:", qr_data)  # Отладочная печать
    try:
        type_id, item_name = qr_data.split(",")
        print(f"type_id: {type_id.strip()}, item_name: {item_name.strip()}")
        return int(type_id.strip()), item_name.strip()
    except ValueError as e:
        print(f"Error parsing qr code: {qr_data} - {e}") # Дополнительная отладочная печать
        return None, None

# 5. Функция для добавления товара в БД
def add_item_to_db(conn, barcodeData):
    """Добавляет товар в базу данных, если его там нет."""
    if conn is None:
        print("No connection to insert items")
        return
    cursor = conn.cursor()
    type_id, item_name = parse_qr_data(barcodeData)
    if type_id is None:
        return # Выходим, если не удалось разобрать qr code
    try:
      timestamp = datetime.datetime.now().isoformat() # Преобразуем datetime в строку
      cursor.execute(
          """
              INSERT OR IGNORE INTO Item (name, type_id, date)
              VALUES (?, ?, ?)
          """, (item_name, type_id, timestamp)
      )
      conn.commit()
      print(f"Added/ignored item: {item_name}, type:{type_id}")
    except sqlite3.Error as e:
        print(f"Error adding item: {e}")



db_connection = create_database_connection('sqrunner.db')

create_database_tables(db_connection)

populate_type_table(db_connection)

ap = argparse.ArgumentParser()
ap.add_argument("-o", "--output", type=str, default="barcodes.csv",
    help="path to output CSV file containing barcodes")
args = vars(ap.parse_args())
vs = VideoStream(usePiCamera=True).start()
time.sleep(2.0)

# Словарь для отслеживания времени последнего сканирования QR-кодов
last_scanned = {}

# Задержка между повторными сканированиями (в секундах)
scan_delay = 5

while True:
    frame = vs.read()
    frame = imutils.resize(frame, width=400)

    cv2.imshow("Barcode Reader", frame)
    key = cv2.waitKey(1) & 0xFF

    if key == ord(" "): # Если нажат пробел
        barcodes = pyzbar.decode(frame)
        for barcode in barcodes:
            (x, y, w, h) = barcode.rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            barcodeData = barcode.data.decode("utf-8")
            barcodeType = barcode.type
            text = "{} ({})".format(barcodeData, barcodeType)
            print(text)
            cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            now = datetime.datetime.now()
            if barcodeData not in last_scanned or (now - last_scanned[barcodeData]).total_seconds() > scan_delay:
                #print(f"Processing QR code: {barcodeData}")
                add_item_to_db(db_connection, barcodeData)
                last_scanned[barcodeData] = now
            else:
                print(f"Skipping duplicate QR code: {barcodeData}")

    if key == ord("s"):
        break

print("[INFO] cleaning up...")
cv2.destroyAllWindows()
vs.stop()

if db_connection:
    db_connection.close()
