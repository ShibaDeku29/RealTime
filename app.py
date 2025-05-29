from flask import Flask, render_template, request, redirect, url_for, session, flash
from config import Config
from extensions import db
from models.user import User
from models.message import Message
from werkzeug.security import generate_password_hash, check_password_hash

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

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
            
            # Kiểm tra nếu username đã tồn tại
            if User.query.filter_by(username=username).first():
                flash('Username already exists!')
                return redirect(url_for('register'))

            # Mã hóa mật khẩu
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

            # Tạo người dùng mới
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
        if request.method == 'POST':
            content = request.form['content']
            msg = Message(content=content, user_id=session['user_id'])
            db.session.add(msg)
            db.session.commit()
        messages = Message.query.order_by(Message.timestamp.desc()).all()
        return render_template('chatroom.html', messages=messages, username=session.get('username'))

    return app

app = create_app()

# Chạy Flask với cổng được Render cấp từ biến môi trường PORT
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
