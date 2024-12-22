import sqlite3
from flask import Flask, render_template
from flask_socketio import SocketIO, send, emit
import datetime
import threading

app = Flask(__name__)
socketio = SocketIO(app)

# Создание базы данных и таблиц, если их еще нет
def init_db():
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()

    # Создание таблиц
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

# Инициализация базы данных
init_db()

@app.route('/')
def index():
    return render_template('index.html')

# Обработка сообщений от клиента
@socketio.on('message')
def handle_message(data):
    """
    При получении сообщения от клиента, сохраняем его в базу данных
    и отправляем всем подключенным клиентам.
    """
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()

    # Сохраняем сообщение в базе данных
    cursor.execute('INSERT INTO messages (username, message) VALUES (?, ?)', 
                   (data['username'], data['message']))
    conn.commit()

    # Получаем все сообщения
    cursor.execute('SELECT id, username, message, timestamp FROM messages ORDER BY timestamp')
    messages = cursor.fetchall()
    conn.close()

    # Отправляем все сообщения всем подключённым клиентам
    emit('all_messages', messages, broadcast=True)

# Получение всех сообщений для пользователя
@socketio.on('get_messages')
def get_messages(username):
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()

    # Получаем все сообщения
    cursor.execute('SELECT id, username, message, timestamp FROM messages ORDER BY timestamp')
    messages = cursor.fetchall()

    # Отправляем все сообщения пользователю
    emit('all_messages', messages)

# Удаление сообщения
@socketio.on('delete_message')
def delete_message(data):
    message_id = data['id']
    username = data['username']

    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()

    cursor.execute('SELECT username FROM messages WHERE id = ?', (message_id,))
    message_owner = cursor.fetchone()

    if message_owner and message_owner[0] == username:
        cursor.execute('DELETE FROM messages WHERE id = ?', (message_id,))
        conn.commit()
        conn.close()

        emit('message_deleted', message_id, broadcast=True)
    else:
        conn.close()

# Редактирование сообщения
@socketio.on('edit_message')
def edit_message(data):
    message_id = data['id']
    new_message = data['message']
    username = data['username']
    
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()

    cursor.execute('SELECT username FROM messages WHERE id = ?', (message_id,))
    message_owner = cursor.fetchone()

    if message_owner and message_owner[0] == username:
        cursor.execute('UPDATE messages SET message = ? WHERE id = ?', (new_message, message_id))
        conn.commit()
        conn.close()

        emit('message_edited', data, broadcast=True)
    else:
        conn.close()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
