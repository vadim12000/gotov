import sqlite3
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, send, emit
import datetime

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
    conn.close()

    # Отправляем сообщение всем пользователям
    send(data, broadcast=True)

# Получение всех сообщений для пользователя, которые он не видел
@socketio.on('get_messages')
def get_messages(username):
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()

    # Получаем все сообщения
    cursor.execute('SELECT id, username, message, timestamp FROM messages ORDER BY timestamp')
    messages = cursor.fetchall()

    # Обновляем время последнего подключения пользователя
    cursor.execute('UPDATE users SET last_seen = ? WHERE username = ?', 
                   (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username))
    conn.commit()
    conn.close()

    # Отправляем все сообщения пользователю
    emit('all_messages', messages)

# Удаление сообщения
@socketio.on('delete_message')
def delete_message(data):
    """
    Удаляем сообщение, но только если оно принадлежит автору.
    """
    message_id = data['id']
    username = data['username']

    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()

    # Проверка, что сообщение принадлежит пользователю
    cursor.execute('SELECT username FROM messages WHERE id = ?', (message_id,))
    message_owner = cursor.fetchone()

    if message_owner and message_owner[0] == username:
        # Удаляем сообщение по ID
        cursor.execute('DELETE FROM messages WHERE id = ?', (message_id,))
        conn.commit()
        conn.close()

        # Отправляем уведомление всем пользователям о удалении сообщения
        emit('message_deleted', message_id, broadcast=True)
    else:
        conn.close()

# Редактирование сообщения
@socketio.on('edit_message')
def edit_message(data):
    """
    Редактируем сообщение, но только если оно принадлежит пользователю.
    """
    message_id = data['id']
    new_message = data['message']
    username = data['username']
    
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()

    # Проверка, что сообщение принадлежит пользователю
    cursor.execute('SELECT username FROM messages WHERE id = ?', (message_id,))
    message_owner = cursor.fetchone()

    if message_owner and message_owner[0] == username:
        # Обновляем сообщение в базе данных
        cursor.execute('UPDATE messages SET message = ? WHERE id = ?', (new_message, message_id))
        conn.commit()
        conn.close()

        # Отправляем уведомление всем пользователям о изменении сообщения
        emit('message_edited', data, broadcast=True)
    else:
        conn.close()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
