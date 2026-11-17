from abc import ABC, abstractmethod
from functools import wraps
import sqlite3

# Декоратор для логирования действий.
# Зачем нужен: чтобы не писать вручную print() внутри каждого метода работы, 
# с базой данных и поиска. Мы просто вешаем @action_logger над нужной функцией,
# и перед её запуском автоматически выводится сообщение, какая операция пошла.

def action_logger(func):

  @wraps(func)
  def wrapper(*args, **kwargs):
    print(f"\n>>> Выполнение операции: {func.__name__}...")
    return func(*args, **kwargs)

  return wrapper


# Абстрактный класс: задаёт общий шаблон для всех элементов библиотеки.
# Зачем нужен: это общий шаблон для всех объектов нашей библиотеки.
# Наследование от ABC и @abstractmethod не дадут создать новый класс без метода
# get_info(). Так мы точно уверены, что любой объект (книга, аудиокнига или
# будущий журнал) умеет красиво выдавать информацию о себе.

class LibraryItem(ABC):

  @abstractmethod
  def get_info(self):
    pass


# Mixin: добавляет объекту умение превращаться в словарь
# Почему сделали отдельным классом: превращение в словарь — это дополнительная
# фишка, а не главная задача книги. Вынеся её в JsonExportMixin, мы можем легко
# подключить это умение к Book и к любым другим классам без копипаста.
class JsonExportMixin:

  def to_dict(self):
    data = {
        "title": self.title,
        "author": self.author,
        "year": self.year,
    }
    if hasattr(self, "duration"):
      data["duration"] = self.duration
    return data


# Базовый класс Book. Использует множественное наследование: берёт обязательный
# метод get_info() от LibraryItem и умение собираться в словарь от JsonExportMixin.

class Book(LibraryItem, JsonExportMixin):

  def __init__(self, title: str, author: str, year: int):
    # Инкапсуляция: прячем название в приватный атрибут
    self.__title = title
    self.author = author

    if not self.is_valid_year(year):
      raise ValueError("Некорректный год выпуска (допустимо 1450–2026).")
    self.year = year

  # @property (геттер и сеттер): позволяет обращаться к названию как к обычному
  # полю (book.title), но при попытке его поменять сеттер сам проверит, чтобы новое название не оказалось пустым.
  @property
  def title(self):
    return self.__title

  @title.setter
  def title(self, new_title: str):
    if not new_title.strip():
      raise ValueError("Название не может быть пустым.")
    self.__title = new_title.strip()

  # @staticmethod: проверяет, адекватный ли год выпуска ввёл пользователь.
  # Сделали статическим, потому что для проверки числа не нужны данные
  # конкретной книги (self) или самого класса (cls) — удобно вызвать заранее.
  @staticmethod
  def is_valid_year(year: int) -> bool:
    return isinstance(year, int) and 1450 <= year <= 2026

  # Метод класса: создание книги из готового словаря, (например, если данные пришли из файла или сети). Принимает сам класс cls
  # и возвращает готовый объект.
  @classmethod
  def from_dict(cls, data: dict):
    return cls(data["title"], data["author"], int(data["year"]))

  def get_info(self) -> str:
    return f"Книга: «{self.title}» | Автор: {self.author} | Год: {self.year}"

  # Магический метод __str__: нужен, чтобы при обычном print(book) выводилась
  # понятная строка с информацией о книге, а не непонятный адрес объекта в памяти.
  def __str__(self) -> str:
    return self.get_info()

 # Магический метод __eq__: учит оператор == сравнивать две книги по их
# названиям (независимо от больших и маленьких букв), а не по адресам в памяти.
  def __eq__(self, other) -> bool:
    if isinstance(other, Book):
      return self.title.lower() == other.title.lower()
    return False


# Дочерний класс AudioBook (наследование и полиморфизм).
# Почему наследуется от Book: у аудиокниги есть те же название, автор и год,
# поэтому нет смысла писать их заново — мы просто берём их у родителя.
# Для чего нужен super(): он запускает конструктор __init__ класса Book, чтобы
# заполнить общие поля и проверить год.
# Зачем добавили duration: это особенность именно аудиокниги (длительность в часах).
# Полиморфизм: мы переопределили метод get_info(), чтобы при одинаковом вызове
# обычная книга и аудиокнига выдавали разный, подходящий им текст.

class AudioBook(Book):

  def __init__(self, title: str, author: str, year: int, duration: float):
    super().__init__(title, author, year)
    self.duration = duration

  # Переопределяем метод вывода информации
  def get_info(self) -> str:
    return f"Аудиокнига: «{self.title}» | Автор: {self.author} | Год: {self.year} | Длительность: {self.duration} ч."


# Класс LibraryDB для работы с базой данных SQLite3 и операциями CRUD.
# Зачем вынесли в отдельный класс: чтобы не смешивать SQL-запросы с меню
# и логикой книг. Выбрали SQLite3, потому что он встроен в Python и хранит
# всё в одном файле library.db — книги не пропадают после закрытия программы.
# Здесь реализованы все 4 операции CRUD:
# - Create (add_book): добавляет новую книгу в таблицу через INSERT.
# - Read (get_all_books): достаёт все строки через SELECT и превращает в объекты.
# - Update (update_book): меняет название, автора и год по ID через UPDATE.
# - Delete (delete_book): удаляет книгу по её ID через DELETE.

class LibraryDB:

  def __init__(self, db_name="library.db"):
    self.conn = sqlite3.connect(db_name)
    self.create_table()
    self.seed_initial_books()

  def create_table(self):
    cursor = self.conn.cursor()
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER NOT NULL,
                book_type TEXT NOT NULL,
                duration REAL
            )
        """)
    self.conn.commit()

  # Заполняем пустую базу тестовыми книгами при самом первом запуске
  def seed_initial_books(self):
    cursor = self.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM books")
    if cursor.fetchone()[0] == 0:
      cursor.execute(
          "INSERT INTO books (title, author, year, book_type, duration) VALUES"
          " ('Белый пароход', 'Чингиз Айтматов', 1970, 'Book', NULL)"
      )
      cursor.execute(
          "INSERT INTO books (title, author, year, book_type, duration) VALUES"
          " ('Мастер и Маргарита', 'Михаил Булгаков', 1967, 'Book', NULL)"
      )
      cursor.execute(
          "INSERT INTO books (title, author, year, book_type, duration) VALUES"
          " ('Дюна', 'Фрэнк Герберт', 1965, 'AudioBook', 21.5)"
      )
      self.conn.commit()

  @action_logger
  def add_book(self, book: Book):
    book_type = "AudioBook" if isinstance(book, AudioBook) else "Book"
    duration = book.duration if isinstance(book, AudioBook) else None

    cursor = self.conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, year, book_type, duration) VALUES"
        " (?, ?, ?, ?, ?)",
        (book.title, book.author, book.year, book_type, duration),
    )
    self.conn.commit()
    print("Книга успешно добавлена!")

  @action_logger
  def get_all_books(self) -> list:
    cursor = self.conn.cursor()
    cursor.execute(
        "SELECT id, title, author, year, book_type, duration FROM books"
    )
    books = []
    for row in cursor.fetchall():
      book_id, title, author, year, book_type, duration = row
      if book_type == "AudioBook":
        books.append((book_id, AudioBook(title, author, year, duration)))
      else:
        books.append((book_id, Book(title, author, year)))
    return books

  @action_logger
  def update_book(self, book_id: int, title: str, author: str, year: int):
    if not Book.is_valid_year(year):
      raise ValueError("Некорректный год выпуска.")
    cursor = self.conn.cursor()
    cursor.execute(
        "UPDATE books SET title = ?, author = ?, year = ? WHERE id = ?",
        (title, author, year, book_id),
    )
    self.conn.commit()
    print(
        "Данные обновлены!"
        if cursor.rowcount
        else "Книга с таким ID не найдена."
    )

  @action_logger
  def delete_book(self, book_id: int):
    cursor = self.conn.cursor()
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    self.conn.commit()
    print(
        "Книга удалена!" if cursor.rowcount else "Книга с таким ID не найдена."
    )


# Поиск книги и сложность алгоритма O(n).
# Как работает: обычный линейный поиск — цикл по очереди перебирает список книг
# с самого начала и сравнивает названия, заодно считая количество проверок.
# Почему сложность O(n): список книг не отсортирован, поэтому в худшем случае
# (если нужная книга в самом конце или её вообще нет) программе придётся
# проверить все n книг. Если книг станет в 10 раз больше, поиск займёт, примерно в 10 раз больше времени.

@action_logger
def find_book_by_title(books_list: list, search_title: str):
  checks = 0
  for book_id, book in books_list:
    checks += 1
    if book.title.lower() == search_title.strip().lower():
      print(f"Найдено за {checks} проверок: [ID: {book_id}] {book}")
      return
  print(f"Книга не найдена. Всего выполнено проверок: {checks}")


# Главная функция с консольным меню: связывает ввод пользователя с базой и классами.

def main():
  db = LibraryDB()

  while True:
    print("\n--- МЕНЮ БИБЛИОТЕКИ ---")
    print("1. Добавить книгу")
    print("2. Добавить аудиокнигу")
    print("3. Показать все книги")
    print("4. Найти книгу по названию")
    print("5. Изменить книгу")
    print("6. Удалить книгу")
    print("7. Тест ООП (Mixin, @classmethod, __eq__)")
    print("0. Выход")

    choice = input("Выберите пункт: ").strip()

    try:
      if choice == "1":
        title = input("Название: ")
        author = input("Автор: ")
        year = int(input("Год выпуска: "))
        db.add_book(Book(title, author, year))

      elif choice == "2":
        title = input("Название: ")
        author = input("Автор: ")
        year = int(input("Год выпуска: "))
        duration = float(input("Длительность (часов): "))
        db.add_book(AudioBook(title, author, year, duration))

      elif choice == "3":
        books = db.get_all_books()
        for book_id, book in books:
          print(f"[ID: {book_id}] {book}")

      elif choice == "4":
        query = input("Введите название для поиска: ")
        books = db.get_all_books()
        find_book_by_title(books, query)

      elif choice == "5":
        book_id = int(input("ID книги: "))
        title = input("Новое название: ")
        author = input("Новый автор: ")
        year = int(input("Новый год: "))
        db.update_book(book_id, title, author, year)

      elif choice == "6":
        book_id = int(input("ID книги для удаления: "))
        db.delete_book(book_id)

      elif choice == "7":
        # Создание книги из словаря (@classmethod)
        data = {"title": "1984", "author": "Джордж Оруэлл", "year": 1949}
        b1 = Book.from_dict(data)
        b2 = Book("1984", "Дж. Оруэлл", 1949)
        print("Из словаря:", b1)
        print("В словарь (Mixin):", b1.to_dict())
        print("Сравнение книг (__eq__):", b1 == b2)

      elif choice == "0":
        print("Работа завершена.")
        break
      else:
        print("Нет такого пункта.")
    except ValueError as e:
      print(f"Ошибка: {e}")


if __name__ == "__main__":
  main()
