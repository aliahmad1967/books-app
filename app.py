import streamlit as st
import sqlite3
import pandas as pd
import io
from datetime import datetime
import base64

# Set page configuration for RTL support
st.set_page_config(layout="wide", initial_sidebar_state="expanded")

# Add custom CSS for RTL support
st.markdown(
    """
    <style>
    body {
        direction: rtl;
    }
    .stTextInput > div > div > input {
        direction: rtl;
    }
    .stSelectbox > div > div > select {
        direction: rtl;
    }
    .stTextArea textarea {
        direction: rtl;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Database connection
def db_connection():
    conn = None
    try:
        conn = sqlite3.connect("books.sqlite")
    except sqlite3.error as e:
        st.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
    return conn

# Create table if not exists
def create_table():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS book (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author TEXT NOT NULL,
        language TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT,
        publish_date DATE,
        notes TEXT,
        image BLOB
    )
    """)
    conn.commit()
    conn.close()

# Function to get all books
def get_all_books():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, author, language, title, summary, publish_date, notes FROM book")
    books = [
        dict(id=row[0], author=row[1], language=row[2], title=row[3], summary=row[4], publish_date=row[5], notes=row[6])
        for row in cursor.fetchall()
    ]
    conn.close()
    return books

# Function to add a new book
def add_book(author, language, title, summary, publish_date, notes, image):
    conn = db_connection()
    cursor = conn.cursor()
    sql = "INSERT INTO book (author, language, title, summary, publish_date, notes, image) VALUES (?, ?, ?, ?, ?, ?, ?)"
    cursor.execute(sql, (author, language, title, summary, publish_date, notes, image))
    conn.commit()
    conn.close()

# Function to update a book
def update_book(id, author, language, title, summary, publish_date, notes, image):
    conn = db_connection()
    cursor = conn.cursor()
    sql = "UPDATE book SET author=?, language=?, title=?, summary=?, publish_date=?, notes=?, image=? WHERE id=?"
    cursor.execute(sql, (author, language, title, summary, publish_date, notes, image, id))
    conn.commit()
    conn.close()

# Function to delete a book
def delete_book(id):
    conn = db_connection()
    cursor = conn.cursor()
    sql = "DELETE FROM book WHERE id=?"
    cursor.execute(sql, (id,))
    conn.commit()
    conn.close()

# Function to get book image
def get_book_image(id):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT image FROM book WHERE id=?", (id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Streamlit app
def main():
    st.title("إدارة الكتب")
    create_table()

    # Sidebar for adding new books and importing data
    with st.sidebar:
        st.header("إضافة كتاب جديد")
        new_author = st.text_input("المؤلف", key="new_author")
        new_language = st.text_input("اللغة", key="new_language")
        new_title = st.text_input("العنوان", key="new_title")
        new_summary = st.text_area("ملخص موجز", key="new_summary")
        new_publish_date = st.date_input("تاريخ النشر", key="new_publish_date")
        new_notes = st.text_area("ملاحظات", key="new_notes")
        new_image = st.file_uploader("صورة الكتاب", type=["jpg", "png", "jpeg"], key="new_image")
        
        if st.button("إضافة كتاب"):
            if new_image is not None:
                image_bytes = new_image.getvalue()
            else:
                image_bytes = None
            add_book(new_author, new_language, new_title, new_summary, new_publish_date, new_notes, image_bytes)
            st.success("تمت إضافة الكتاب بنجاح")

        st.header("استيراد البيانات")
        uploaded_file = st.file_uploader("اختر ملف CSV", type="csv", key="csv_upload")
        if uploaded_file is not None:
            data = pd.read_csv(uploaded_file)
            conn = db_connection()
            data.to_sql("book", conn, if_exists="append", index=False)
            conn.close()
            st.success("تم استيراد البيانات بنجاح")

    # Main content
    books = get_all_books()
    df = pd.DataFrame(books)

    # Display books table
    st.header("قائمة الكتب")
    st.dataframe(df)

    # Book details
    st.header("تفاصيل الكتاب")
    selected_book_id = st.selectbox("اختر كتابًا", options=[book["id"] for book in books], format_func=lambda x: next(book["title"] for book in books if book["id"] == x), key="book_select")
    
    if selected_book_id:
        book = next(book for book in books if book["id"] == selected_book_id)
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader(book["title"])
            st.write(f"المؤلف: {book['author']}")
            st.write(f"اللغة: {book['language']}")
            st.write(f"تاريخ النشر: {book['publish_date']}")
            st.subheader("ملخص")
            st.write(book["summary"])
            st.subheader("ملاحظات")
            st.write(book["notes"])
        
        with col2:
            image = get_book_image(selected_book_id)
            if image:
                st.image(image, caption="صورة الكتاب", use_column_width=True)
            else:
                st.write("لا توجد صورة متاحة")

    # Edit and delete options
    st.header("تحرير أو حذف كتاب")
    book_id = st.number_input("أدخل معرف الكتاب", min_value=1, step=1, key="book_id_input")
    action = st.radio("اختر الإجراء", ("تحرير", "حذف"), key="action_radio")

    if action == "تحرير":
        book = next((b for b in books if b["id"] == book_id), None)
        if book:
            edit_author = st.text_input("المؤلف", value=book["author"], key="edit_author")
            edit_language = st.text_input("اللغة", value=book["language"], key="edit_language")
            edit_title = st.text_input("العنوان", value=book["title"], key="edit_title")
            edit_summary = st.text_area("ملخص موجز", value=book["summary"], key="edit_summary")
            edit_publish_date = st.date_input("تاريخ النشر", value=datetime.strptime(book["publish_date"], "%Y-%m-%d") if book["publish_date"] else None, key="edit_publish_date")
            edit_notes = st.text_area("ملاحظات", value=book["notes"], key="edit_notes")
            edit_image = st.file_uploader("تحديث صورة الكتاب", type=["jpg", "png", "jpeg"], key="edit_image")
            
            if st.button("تحديث الكتاب"):
                image = get_book_image(book_id)
                if edit_image is not None:
                    image = edit_image.getvalue()
                update_book(book_id, edit_author, edit_language, edit_title, edit_summary, edit_publish_date, edit_notes, image)
                st.success("تم تحديث الكتاب بنجاح")
        else:
            st.warning("لم يتم العثور على الكتاب")

    elif action == "حذف":
        if st.button("حذف الكتاب"):
            delete_book(book_id)
            st.success("تم حذف الكتاب بنجاح")

if __name__ == "__main__":
    main()