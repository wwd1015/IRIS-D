from flask import Flask, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import os
from functools import wraps

class User(UserMixin):
    def __init__(self, user_id, username, email, assigned_portfolios, role):
        self.id = user_id
        self.username = username
        self.email = email
        self.assigned_portfolios = assigned_portfolios
        self.role = role

class AuthManager:
    def __init__(self, app):
        self.app = app
        self.login_manager = LoginManager()
        self.login_manager.init_app(app)
        self.login_manager.login_view = '/login'
        
        # Load user data
        self.users = self.load_users()
        
        @self.login_manager.user_loader
        def load_user(user_id):
            return self.get_user_by_id(user_id)
    
    def load_users(self):
        """Load users from CSV file"""
        try:
            if os.path.exists('data/user_mapping.csv'):
                df = pd.read_csv('data/user_mapping.csv')
                users = {}
                for _, row in df.iterrows():
                    # Convert string representation of list back to list
                    portfolios = eval(row['assigned_portfolios']) if isinstance(row['assigned_portfolios'], str) else row['assigned_portfolios']
                    
                    # Generate a simple password for demo (in production, use proper password management)
                    password_hash = generate_password_hash('password123')
                    
                    users[row['user_id']] = {
                        'user_id': row['user_id'],
                        'username': row['username'],
                        'email': row['email'],
                        'assigned_portfolios': portfolios,
                        'role': row['role'],
                        'password_hash': password_hash
                    }
                return users
            else:
                # Create default admin user if no data exists
                return {
                    'admin': {
                        'user_id': 'admin',
                        'username': 'admin',
                        'email': 'admin@bank.com',
                        'assigned_portfolios': ['Portfolio_1', 'Portfolio_2', 'Portfolio_3'],
                        'role': 'Director',
                        'password_hash': generate_password_hash('admin123')
                    }
                }
        except Exception as e:
            print(f"Error loading users: {e}")
            return {}
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        if user_id in self.users:
            user_data = self.users[user_id]
            return User(
                user_data['user_id'],
                user_data['username'],
                user_data['email'],
                user_data['assigned_portfolios'],
                user_data['role']
            )
        return None
    
    def authenticate_user(self, username, password):
        """Authenticate user with username and password"""
        for user_id, user_data in self.users.items():
            if user_data['username'] == username:
                if check_password_hash(user_data['password_hash'], password):
                    return self.get_user_by_id(user_id)
        return None
    
    def get_user_portfolios(self, user_id):
        """Get portfolios assigned to a user"""
        if user_id in self.users:
            return self.users[user_id]['assigned_portfolios']
        return []
    
    def has_portfolio_access(self, user_id, portfolio):
        """Check if user has access to specific portfolio"""
        user_portfolios = self.get_user_portfolios(user_id)
        return portfolio in user_portfolios

def portfolio_access_required(portfolio_param='portfolio'):
    """Decorator to check portfolio access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            
            portfolio = request.args.get(portfolio_param) or kwargs.get(portfolio_param)
            if portfolio and not AuthManager.has_portfolio_access(current_user.id, portfolio):
                flash('Access denied to this portfolio', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def create_auth_routes(app, auth_manager):
    """Create authentication routes"""
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            user = auth_manager.authenticate_user(username, password)
            if user:
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
        
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bank Risk Dashboard - Login</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body { background-color: #f8f9fa; }
                .login-container { 
                    max-width: 400px; 
                    margin: 100px auto; 
                    padding: 20px;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }
                .bank-logo { text-align: center; margin-bottom: 30px; }
                .bank-logo h2 { color: #2c3e50; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="login-container">
                    <div class="bank-logo">
                        <h2>🏦 Bank Risk Dashboard</h2>
                        <p class="text-muted">Risk Management Portal</p>
                    </div>
                    
                    <form method="POST">
                        <div class="mb-3">
                            <label for="username" class="form-label">Username</label>
                            <input type="text" class="form-control" id="username" name="username" required>
                        </div>
                        <div class="mb-3">
                            <label for="password" class="form-label">Password</label>
                            <input type="password" class="form-control" id="password" name="password" required>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Login</button>
                    </form>
                    
                    <div class="mt-3 text-center">
                        <small class="text-muted">
                            Demo credentials:<br>
                            Username: admin, Password: admin123<br>
                            Username: risk_analyst_1, Password: password123
                        </small>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out', 'info')
        return redirect(url_for('login'))
    
    return app 