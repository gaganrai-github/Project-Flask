from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_please_change_this_to_a_strong_secret' # IMPORTANT: Change this!

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'user_login'

# Define file paths
# Ensure these directories exist or are created by your application
USER_DATA_FILE = 'data/Users/users.json'
ADMIN_DATA_FILE = 'data/Users/admin.json'
SERVICES_DATA_FILE = 'data/services.json'
COLLECTED_DATA_DIR = 'data/collected_forms' # Changed to a more specific directory for collected data

# Ensure data directories exist on startup
os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)
os.makedirs(os.path.dirname(ADMIN_DATA_FILE), exist_ok=True)
os.makedirs(os.path.dirname(SERVICES_DATA_FILE), exist_ok=True)
os.makedirs(COLLECTED_DATA_DIR, exist_ok=True)


# User model for Flask-Login
class User(UserMixin):
    def __init__(self, id, name, password, is_admin):
        self.id = id
        self.name = name
        self.password = password
        self.is_admin = is_admin

    def get_id(self):
        return str(self.id) # Flask-Login expects string IDs

# --- Data Loading/Saving Helpers ---
def load_json_data(filepath, default_value):
    """Loads JSON data from a file. Handles missing files and JSON decoding errors."""
    if not os.path.exists(filepath):
        return default_value
    with open(filepath, 'r') as f:
        try:
            # Handle empty file specifically, load_json_data can fail if file is empty
            content = f.read()
            if not content:
                return default_value
            return json.loads(content)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {filepath}. Returning default value.")
            return default_value # Return default if file is empty or malformed

def save_json_data(filepath, data):
    """Saves data to a JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True) # Ensure directory exists
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def load_users():
    return load_json_data(USER_DATA_FILE, {}) # Users are stored as a dictionary

def save_users(users):
    save_json_data(USER_DATA_FILE, users)

def load_admins():
    return load_json_data(ADMIN_DATA_FILE, {}) # Admins are stored as a dictionary

def save_admins(admins):
    save_json_data(ADMIN_DATA_FILE, admins)

def load_services():
    return load_json_data(SERVICES_DATA_FILE, {}) # Services are stored as a dictionary

def save_services(services):
    save_json_data(SERVICES_DATA_FILE, services)

# Flask-Login user loader function
@login_manager.user_loader
def load_user(user_id):
    """Loads a user from the ID stored in the session."""
    admins = load_admins()
    if user_id in admins:
        a = admins[user_id]
        return User(id=user_id, name=a.get('username', 'Admin'), password=a['password'], is_admin=True)

    users = load_users()
    if user_id in users:
        u = users[user_id]
        return User(id=user_id, name=u.get('username'), password=u['password'], is_admin=False)

    return None

# Decorator to restrict access to admin users
def admin_required(f):
    """Decorator to protect routes for admin users only."""
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have administrative access.', 'error')
            return redirect(url_for('user_dashboard')) # Redirect to user dashboard if not admin
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__ # Preserve original function name for Flask
    return decorated_function

# --- ROUTES ---

@app.route('/')
def index():
    """Renders the home page with a list of services."""
    services = load_services()
    services_list = []
    # Pre-process services to include full image paths and animation delays
    for i, (service_id, service_data) in enumerate(services.items()):
        service_info = {'id': service_id, **service_data}
        # Generate full static URL for the image
        if 'image' in service_info and service_info['image']:
            service_info['image_url'] = url_for('static', filename=f'images/{service_info["image"]}')
        else:
            service_info['image_url'] = url_for('static', filename='images/default.jpg') # Fallback image
        # Calculate animation delay
        service_info['animation_delay'] = f"{((i + 1) * 0.1):.1f}s"
        services_list.append(service_info)

    return render_template('index.html', services=services_list)

@app.route('/login')
def login():
    """Renders the login page."""
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        users = load_users()
        admins = load_admins()

        # Check if email already exists for any user or admin
        if any(user_data.get('email') == email for user_data in users.values()) or \
           any(admin_data.get('email') == email for admin_data in admins.values()):
            flash('User with this email already exists. Please use a different email or log in.', 'error')
            return redirect(url_for('register'))

        # Generate a unique user ID
        # Convert keys to integers, add a default 0 in case lists are empty, find max, then add 1
        all_ids = [int(uid) for uid in list(users.keys()) + list(admins.keys()) if uid.isdigit()]
        new_user_id = str(max(all_ids + [0]) + 1)

        hashed_password = generate_password_hash(password)

        users[new_user_id] = { # New registrations are always regular users
            'username': username,
            'email': email,
            'password': hashed_password
        }
        save_users(users)
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('user_login'))

    return render_template('register.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    """Handles admin login."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        admins = load_admins()
        for uid, admin in admins.items():
            if admin.get('email') == email and check_password_hash(admin.get('password', ''), password):
                user_obj = User(id=uid, name=admin.get('username', 'Admin'), password=admin.get('password'), is_admin=True)
                login_user(user_obj)
                flash('Logged in as Admin.', 'success')
                return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials.', 'error')
    return render_template('login/admin_login.html')

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    """Handles regular user login."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        users = load_users()
        for uid, user in users.items():
            if user.get('email') == email and check_password_hash(user.get('password', ''), password):
                user_obj = User(id=uid, name=user.get('username', 'User'), password=user.get('password'), is_admin=False)
                login_user(user_obj)
                flash('Logged in successfully.', 'success')
                return redirect(url_for('user_dashboard'))

    flash('Invalid credentials.', 'error')
    return render_template('login/user_login.html')

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    """Renders the user dashboard."""
    return render_template('login/dashboard/user_dashboard.html', name=current_user.name)

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    """Renders the admin dashboard."""
    return render_template('login/dashboard/admin_dashboard.html', name=current_user.name)

# --- ADMIN CRUD OPERATIONS FOR USERS ---
@app.route('/admin/users')
@admin_required
def manage_users():
    """Manages users (admin view)."""
    users = load_users()
    admins = load_admins()
    all_users_list = []
    for uid, data in users.items():
        all_users_list.append({'id': uid, 'username': data.get('username'), 'email': data.get('email'), 'is_admin': False})
    for uid, data in admins.items():
        all_users_list.append({'id': uid, 'username': data.get('username'), 'email': data.get('email'), 'is_admin': True})
    # Sort by ID to maintain a consistent order
    all_users_list.sort(key=lambda x: int(x['id']))
    return render_template('admin/manage_users.html', users=all_users_list)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    """Adds a new user or admin."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = request.form.get('is_admin') == 'on' # Checkbox value 'on' if checked

        users = load_users()
        admins = load_admins()

        # Check for duplicate emails across both user and admin lists
        if any(user.get('email') == email for user in users.values()) or \
           any(admin.get('email') == email for admin in admins.values()):
            flash('A user or admin with this email already exists.', 'error')
            return redirect(url_for('add_user'))

        # Generate a new unique ID
        all_ids = [int(uid) for uid in list(users.keys()) + list(admins.keys()) if uid.isdigit()]
        new_user_id = str(max(all_ids + [0]) + 1)

        hashed_password = generate_password_hash(password)

        user_data_to_save = {
            'username': username,
            'email': email,
            'password': hashed_password
        }

        if is_admin:
            admins[new_user_id] = user_data_to_save
            save_admins(admins)
        else:
            users[new_user_id] = user_data_to_save
            save_users(users)

        flash('User added successfully!', 'success')
        return redirect(url_for('manage_users'))
    return render_template('admin/add_user.html')

@app.route('/admin/users/edit/<string:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edits an existing user or admin."""
    users = load_users()
    admins = load_admins()

    user_data = None
    is_current_user_admin_in_file = False # Flag to track if the user_id points to an admin currently
    if user_id in users:
        user_data = users[user_id]
    elif user_id in admins:
        user_data = admins[user_id]
        is_current_user_admin_in_file = True
    else:
        flash('User not found.', 'error')
        return redirect(url_for('manage_users'))

    if request.method == 'POST':
        new_username = request.form.get('username')
        new_email = request.form.get('email')
        new_password = request.form.get('password')
        new_is_admin = request.form.get('is_admin') == 'on'

        # Check for duplicate emails against all *other* users/admins
        for uid, u_data in users.items():
            if uid != user_id and u_data.get('email') == new_email:
                flash('Another user with this email already exists.', 'error')
                return redirect(url_for('edit_user', user_id=user_id))
        for uid, a_data in admins.items():
            if uid != user_id and a_data.get('email') == new_email:
                flash('Another admin with this email already exists.', 'error')
                return redirect(url_for('edit_user', user_id=user_id))

        # Update fields if provided
        if new_username:
            user_data['username'] = new_username
        if new_email:
            user_data['email'] = new_email
        if new_password: # Only update password if a new one is provided
            user_data['password'] = generate_password_hash(new_password)

        # Handle changing user type (regular user <-> admin)
        if is_current_user_admin_in_file and not new_is_admin:
            # Was admin, now regular user
            del admins[user_id]
            users[user_id] = user_data
            save_admins(admins)
            save_users(users)
        elif not is_current_user_admin_in_file and new_is_admin:
            # Was regular user, now admin
            del users[user_id]
            admins[user_id] = user_data
            save_users(users)
            save_admins(admins)
        elif is_current_user_admin_in_file:
            # Remains admin, update in admins
            admins[user_id] = user_data
            save_admins(admins)
        else:
            # Remains regular user, update in users
            users[user_id] = user_data
            save_users(users)

        flash('User updated successfully!', 'success')
        return redirect(url_for('manage_users'))

    # GET request: render the edit form
    return render_template('admin/edit_user.html', user=user_data, user_id=user_id, is_admin=is_current_user_admin_in_file)

@app.route('/admin/users/delete/<string:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Deletes a user or admin."""
    users = load_users()
    admins = load_admins()

    # Prevent admin from deleting their own account while logged in
    if current_user.is_admin and current_user.id == user_id:
        flash("You cannot delete your own admin account.", "error")
        return redirect(url_for('manage_users'))

    if user_id in users:
        del users[user_id]
        save_users(users)
        flash('User deleted successfully!', 'success')
    elif user_id in admins:
        del admins[user_id]
        save_admins(admins)
        flash('Admin user deleted successfully!', 'success')
    else:
        flash('User not found.', 'error')

    return redirect(url_for('manage_users'))

# --- ADMIN CRUD OPERATIONS FOR SERVICES ---

# Define service types and their specific fields (excluding common ones like title, price, description, image)
SERVICE_TYPES = {
    'general': [], # No specific fields
    'movie_downloader': ['website_link', 'features_list'], # features_list will be comma-separated
    'youtube_downloader': ['website_link', 'supported_formats'], # supported_formats will be comma-separated
    'coding_project': ['github_link', 'tech_stack', 'live_demo_link'] # tech_stack will be comma-separated
}

@app.route('/admin/services')
@admin_required
def manage_services():
    """Manages services (admin view)."""
    services = load_services()
    services_list = [{'id': k, **v} for k, v in services.items()]
    return render_template('admin/manage_services.html', services=services_list)

@app.route('/admin/services/add', methods=['GET', 'POST'])
@admin_required
def add_service():
    """Adds a new service."""
    if request.method == 'POST':
        service_type = request.form.get('service_type')
        title = request.form.get('title')
        price = request.form.get('price')
        description = request.form.get('description')
        image = request.form.get('image') # This should be just the filename, e.g., 'my_image.jpg'

        if service_type not in SERVICE_TYPES:
            flash('Invalid service type selected.', 'error')
            return redirect(url_for('add_service'))

        services = load_services()
        # Generate new service ID
        all_service_ids = [int(sid) for sid in services.keys() if sid.isdigit()]
        new_service_id = str(max(all_service_ids + [0]) + 1)

        new_service_data = {
            'type': service_type,
            'title': title,
            'price': price,
            'description': description,
            'image': image # Store just the filename
        }

        # Add type-specific fields
        for field in SERVICE_TYPES[service_type]:
            # Clean up comma-separated lists if applicable
            if field in ['features_list', 'supported_formats', 'tech_stack']:
                value = request.form.get(field, '').strip()
                new_service_data[field] = [item.strip() for item in value.split(',') if item.strip()]
            else:
                new_service_data[field] = request.form.get(field)

        services[new_service_id] = new_service_data
        save_services(services)
        flash('Service added successfully!', 'success')
        return redirect(url_for('manage_services'))

    return render_template('admin/add_service.html', service_types=SERVICE_TYPES.keys())

@app.route('/admin/services/edit/<string:service_id>', methods=['GET', 'POST'])
@admin_required
def edit_service(service_id):
    """Edits an existing service."""
    services = load_services()
    service_data = services.get(service_id)

    if not service_data:
        flash('Service not found.', 'error')
        return redirect(url_for('manage_services'))

    if request.method == 'POST':
        # Get the original type, as type conversion is complex and usually not done in simple edit
        original_service_type = service_data.get('type', 'general')

        service_data['title'] = request.form.get('title')
        service_data['price'] = request.form.get('price')
        service_data['description'] = request.form.get('description')
        service_data['image'] = request.form.get('image') # This should be just the filename

        # Update type-specific fields based on the *original* type of the service
        # If a field is removed from the form for a different type, it will persist
        # unless explicitly handled here. For simplicity, we update based on original type.
        if original_service_type in SERVICE_TYPES:
            for field in SERVICE_TYPES[original_service_type]:
                # Handle comma-separated lists
                if field in ['features_list', 'supported_formats', 'tech_stack'] and isinstance(service_data.get(field), list):
                    value = request.form.get(field, '').strip()
                    service_data[field] = [item.strip() for item in value.split(',') if item.strip()]
                else:
                    service_data[field] = request.form.get(field)

        services[service_id] = service_data
        save_services(services)
        flash('Service updated successfully!', 'success')
        return redirect(url_for('manage_services'))

    # Prepare for GET request: pass service_types and existing service_data
    # Ensure specific fields are converted to comma-separated string for form display
    display_service_data = service_data.copy()
    current_service_type = display_service_data.get('type', 'general')
    if current_service_type in SERVICE_TYPES:
        for field in SERVICE_TYPES[current_service_type]:
            if field in ['features_list', 'supported_formats', 'tech_stack'] and isinstance(display_service_data.get(field), list):
                display_service_data[field] = ", ".join(display_service_data[field])

    return render_template('admin/edit_service.html',
                           service=display_service_data,
                           service_id=service_id,
                           service_types=SERVICE_TYPES.keys(),
                           specific_fields=SERVICE_TYPES.get(current_service_type, [])
                          )

@app.route('/admin/services/delete/<string:service_id>', methods=['POST'])
@admin_required
def delete_service(service_id):
    """Deletes a service."""
    services = load_services()
    if service_id in services:
        del services[service_id]
        save_services(services)
        flash('Service deleted successfully!', 'success')
    else:
        flash('Service not found.', 'error')
    return redirect(url_for('manage_services'))

# --- ADMIN VIEW & CRUD COLLECTED DATA ---
def load_json_data(filepath, default_value=None):
    """Loads JSON data from a file."""
    if default_value is None:
        default_value = [] # Default to an empty list for collected data
    try:
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"DEBUG: Successfully loaded data from {filepath}. Data type: {type(data)}")
                return data
        else:
            print(f"DEBUG: File does not exist or is empty: {filepath}")
            return default_value
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON decoding error in {filepath}: {e}")
        return default_value
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while loading {filepath}: {e}")
        return default_value

@app.route('/admin/view_collected_data')
# @admin_required # Uncomment if you have this decorator
def view_collected_data():
    """Views all collected data from forms."""
    data = {}
    data_files_map = { 
        'Personal Information': 'personal_data.json',
        'Contact Information': 'contact_data.json',
        'Google Logins': 'google_data.json',
        'Facebook Logins': 'facebook_data.json'
    }

    print(f"\n--- DEBUGGING VIEW_COLLECTED_DATA ---")
    print(f"COLLECTED_DATA_DIR: {COLLECTED_DATA_DIR}")
    
    # Check if the directory itself exists
    if not os.path.exists(COLLECTED_DATA_DIR):
        print(f"ERROR: COLLECTED_DATA_DIR does not exist: {COLLECTED_DATA_DIR}")
        flash("Error: Data collection directory not found.", "error")
        return render_template('admin/view_collected_data.html', collected_data={})

    # List files in the directory to see what's there
    try:
        found_files = os.listdir(COLLECTED_DATA_DIR)
        print(f"Files found in COLLECTED_DATA_DIR: {found_files}")
    except Exception as e:
        print(f"ERROR: Could not list directory {COLLECTED_DATA_DIR}: {e}")
        flash("Error: Cannot access data collection directory.", "error")
        return render_template('admin/view_collected_data.html', collected_data={})


    for category, filename in data_files_map.items():
        filepath = os.path.join(COLLECTED_DATA_DIR, filename)
        print(f"\nProcessing category '{category}', file: {filepath}")
        
        loaded_data = load_json_data(filepath, default_value=[]) # Ensure default is an empty list
        
        # Ensure loaded_data is always a list for consistent processing in template
        if not isinstance(loaded_data, list):
            print(f"WARNING: Data for {filename} was not a list ({type(loaded_data)}). Converting to list.")
            loaded_data = [loaded_data] if loaded_data is not None else []
        
        # Filter out any None or non-dictionary items if necessary (optional, but good for robustness)
        cleaned_data = [item for item in loaded_data if isinstance(item, dict)]

        data[category] = [
            {
                'original_filename': filename,
                'original_index': idx,
                'data': item 
            } for idx, item in enumerate(cleaned_data)
        ]
        print(f"  Final items for '{category}': {len(data[category])} entries")

    print(f"--- FINISHED VIEW_COLLECTED_DATA DEBUG ---")
    return render_template('admin/view_collected_data.html', collected_data=data)

@app.route('/admin/collected_data/edit/<string:filename>/<int:index>', methods=['GET', 'POST'])
@admin_required
def edit_collected_entry(filename, index):
    """Edits a specific entry in a collected data file."""
    filepath = os.path.join(COLLECTED_DATA_DIR, filename)
    if not os.path.exists(filepath):
        flash(f'Data file "{filename}" not found.', 'error')
        return redirect(url_for('view_collected_data'))

    file_data = load_json_data(filepath, default_value=[])
    if not isinstance(file_data, list):
        file_data = [file_data] if file_data else [] # Ensure it's a list for consistent indexing

    if not (0 <= index < len(file_data)):
        flash('Entry index out of range.', 'error')
        return redirect(url_for('view_collected_data'))

    entry_to_edit = file_data[index]

    if request.method == 'POST':
        updated_entry = {}
        # Iterate over the original entry's keys to get values from the form
        for key in entry_to_edit.keys():
            # Get value from form, default to original if not present (e.g., timestamp/ip usually hidden)
            updated_entry[key] = request.form.get(key, entry_to_edit.get(key))

        file_data[index] = updated_entry
        save_json_data(filepath, file_data)
        flash(f'Entry in {filename} updated successfully!', 'success')
        return redirect(url_for('view_collected_data'))

    # GET request: Render the edit form
    return render_template('admin/edit_collected_entry.html',
                           entry=entry_to_edit,
                           filename=filename,
                           index=index,
                           category_name=filename.replace('.json', '').replace('_', ' ').title()
                          )

@app.route('/admin/collected_data/delete', methods=['POST'])
@admin_required
def delete_collected_entry():
    """Deletes a specific entry from a collected data file."""
    filename = request.form.get('filename')
    index_str = request.form.get('index')

    if not filename or index_str is None:
        flash('Invalid delete request parameters.', 'error')
        return redirect(url_for('view_collected_data'))

    try:
        index = int(index_str)
    except ValueError:
        flash('Invalid index provided for deletion.', 'error')
        return redirect(url_for('view_collected_data'))

    filepath = os.path.join(COLLECTED_DATA_DIR, filename)

    if not os.path.exists(filepath):
        flash(f'Data file "{filename}" not found.', 'error')
        return redirect(url_for('view_collected_data'))

    try:
        file_data = load_json_data(filepath, default_value=[])
        if not isinstance(file_data, list):
            file_data = [file_data] if file_data else []

        if 0 <= index < len(file_data):
            file_data.pop(index)
            save_json_data(filepath, file_data)
            flash(f'Entry from {filename} deleted successfully!', 'success')
        else:
            flash('Entry index out of range for deletion.', 'error')
    except Exception as e:
        flash(f'An unexpected error occurred during deletion: {e}', 'error')

    return redirect(url_for('view_collected_data'))


# --- EXISTING DATA COLLECTION ROUTES ---

# Helper function to save general data to JSON files (appending to a list)
def save_to_json_list(filename, data):
    """Appends a dictionary to a JSON file that is expected to be a list."""
    filepath = os.path.join(COLLECTED_DATA_DIR, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True) # Ensure directory exists

    existing_data = load_json_data(filepath, []) # Load as a list, default to empty list

    if not isinstance(existing_data, list):
        # If for some reason the file wasn't a list, convert it to one
        existing_data = [existing_data] if existing_data else []

    existing_data.append(data)
    save_json_data(filepath, existing_data)

@app.route('/personal', methods=['GET', 'POST'])
def personal():
    """Collects personal information."""
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
        save_to_json_list('personal_data.json', data)
        flash('Personal info saved successfully!', 'success')
        return redirect(url_for('personal'))
    return render_template('forms/personal.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Collects contact information."""
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
        save_to_json_list('contact_data.json', data)
        flash('Contact info saved successfully!', 'success')
        return redirect(url_for('contact'))
    return render_template('forms/contact.html')

@app.route('/google-login', methods=['GET', 'POST'])
def google_login():
    """Collects Google login data (for testing/demo purposes)."""
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
        save_to_json_list('google_data.json', data)
        flash('Google login data saved (for testing purposes only).', 'success')
        return redirect(url_for('google_login'))
    return render_template('idp/google.html')

@app.route('/facebook-login', methods=['GET', 'POST'])
def facebook_login():
    """Collects Facebook login data (for testing/demo purposes)."""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['pass'] # Note: 'pass' is the name in Facebook's form
        ip = request.remote_addr
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        data = {
            'email': email,
            'password': password,
            'ip': ip,
            'timestamp': timestamp
        }
        save_to_json_list('facebook_data.json', data)
        flash('Facebook login data saved (for testing purposes only).', 'success')
        return redirect(url_for('facebook_login'))
    return render_template('idp/facebook.html')


# --- Other Application Routes ---
@app.route('/logout')
@login_required
def logout():
    """Logs the current user out."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/login-options')
@login_required
def login_options():
    """Page showing various login options."""
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

@app.route('/instagram-login', methods=['GET', 'POST'])
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

# New route for the "Buy Now" button
@app.route("/buy/<string:service_id>")
def buy_service(service_id):
    # In a real application, you'd handle payment processing,
    # adding to cart, user authentication, etc., here.
    
    services = load_services() # Load your services data
    service = services.get(service_id)
    
    if service:
        flash(f"You clicked 'Buy Now' for: {service['title']}! (This is a placeholder action)", "success")
    else:
        flash("Service not found!", "danger")
    return redirect(url_for('index')) # Redirect back to the index page or a confirmation page

@app.route('/service/<string:service_id>')
def service_detail(service_id):
    """Displays details for a specific service."""
    services = load_services()
    service = services.get(service_id)
    if not service:
        flash('Service not found.', 'error')
        return redirect(url_for('index')) # Redirect to home if service not found

    # Ensure image_url is prepared for service_detail page as well
    if 'image' in service and service['image']:
        service['image_url'] = url_for('static', filename=f'images/{service["image"]}')
    else:
        service['image_url'] = url_for('static', filename='images/default.jpg')

    # Convert list fields back to comma-separated strings for display if needed
    display_service = service.copy()
    current_service_type = display_service.get('type', 'general')
    if current_service_type in SERVICE_TYPES:
        for field in SERVICE_TYPES[current_service_type]:
            if field in ['features_list', 'supported_formats', 'tech_stack'] and isinstance(display_service.get(field), list):
                display_service[field] = ", ".join(display_service[field])


    # Pass the entire SERVICE_TYPES map to the template for conditional rendering
    return render_template('service_detail.html', service=display_service, service_types_map=SERVICE_TYPES)


if __name__ == '__main__':
    # Initialize an admin if one doesn't exist for easy testing
    admin_users = load_admins()
    if not admin_users:
        print("No admin found. Creating a default admin...")
        default_admin_id = "1"
        default_admin_email = "admin@example.com"
        default_admin_password = "adminpassword"

        admins = {
            default_admin_id: {
                'username': 'Default Admin',
                'email': default_admin_email,
                'password': generate_password_hash(default_admin_password) # HASH THE PASSWORD!
            }
        }
        save_admins(admins)
        print(f"Default admin created: email={default_admin_email}, password={default_admin_password}")

    app.run(debug=True) # Run Flask app in debug mode