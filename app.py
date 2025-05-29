from flask import Flask, render_template, request, redirect, url_for, flash
from flask_socketio import SocketIO, send
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
import os
from datetime import datetime

# Models
from models.user import User
from models.message import Message

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
socketio = SocketIO(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
@login_required
def index():
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    return render_template("chatroom.html", messages=messages, username=current_user.username)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("index"))
        flash("Đăng nhập thất bại!")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            flash("Tên đã tồn tại.")
        else:
            hashed = generate_password_hash(password)
            new_user = User(username=username, password=hashed)
            db.session.add(new_user)
            db.session.commit()
            flash("Đăng ký thành công! Đăng nhập nhé.")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@socketio.on('message')
def handle_message(msg):
    if current_user.is_authenticated:
        message = Message(content=msg, user_id=current_user.id, username=current_user.username)
        db.session.add(message)
        db.session.commit()
        send(f"{current_user.username}: {msg}", broadcast=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    socketio.run(app, host="0.0.0.0", port=port)
