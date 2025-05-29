# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO
from config import Config
from extensions import db
from models.user import User
from models.message import Message
from werkzeug.security import generate_password_hash, check_password_hash
import os
import eventlet

eventlet.monkey_patch() # Đảm bảo dòng này nằm ở đầu tiên sau các import cơ bản

# Khởi tạo SocketIO ở đây
socketio = SocketIO(manage_session=False) # Không truyền app vào đây ngay

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    socketio.init_app(app) # Khởi tạo SocketIO với app ở đây

    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('chat'))
        return redirect(url_for('login'))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists!')
                return redirect(url_for('register'))

            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            flash('Register successful!')
            return redirect(url_for('login'))
        
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['username'] = user.username
                return redirect(url_for('chat'))
            else:
                flash('Invalid credentials!')
                return redirect(url_for('login'))
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.route('/chat', methods=['GET', 'POST'])
    def chat():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        # Xử lý tin nhắn POST (lưu vào DB)
        if request.method == 'POST':
            content = request.form['content']
            msg = Message(content=content, user_id=session['user_id'])
            db.session.add(msg)
            db.session.commit()
            # Quan trọng: Không cần gửi qua socketio ở đây, vì việc gửi qua socketio sẽ được xử lý bởi `handle_message` event
        messages = Message.query.order_by(Message.timestamp.desc()).all()
        return render_template('chatroom.html', messages=messages, username=session.get('username'))

    @socketio.on('message')
    def handle_message(message):
        # Lưu tin nhắn vào DB khi nhận được qua WebSocket
        # Cần có ngữ cảnh ứng dụng và yêu cầu để truy cập session và db
        # Đây là nơi lỗi RuntimeContext có thể xảy ra nếu không có ngữ cảnh đúng
        with app.app_context(): # Tạo ngữ cảnh ứng dụng
            if 'user_id' in session: # Cần request context để truy cập session
                # Lưu ý: socketio.on('message') không có request context mặc định
                # Bạn sẽ cần truyền thông tin user_id từ client hoặc tìm cách khác
                # Cách đơn giản nhất là gửi username và content từ client
                # Hoặc dùng Flask-Login
                
                # Giả định tin nhắn đến đã bao gồm username: "username: content"
                parts = message.split(':', 1)
                if len(parts) == 2:
                    username = parts[0].strip()
                    content = parts[1].strip()
                    user = User.query.filter_by(username=username).first()
                    if user:
                        msg_db = Message(content=content, user_id=user.id)
                        db.session.add(msg_db)
                        db.session.commit()
                        socketio.emit('message', {'data': f"{username}: {content}"})
                    else:
                        print(f"User '{username}' not found for message: {message}")
                        socketio.emit('message', {'data': f"Ẩn danh: {content}"}) # Vẫn gửi đi nhưng ghi ẩn danh
                else:
                     # Nếu tin nhắn không đúng định dạng "username: content"
                    socketio.emit('message', {'data': message})
            else:
                socketio.emit('message', {'data': message}) # Gửi tin nhắn mà không có user_id

    return app

app = create_app()

port = int(os.environ.get("PORT", 5000))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Chạy socketio.run với đối tượng socketio đã được khởi tạo đúng
    socketio.run(app, host='0.0.0.0', port=port)