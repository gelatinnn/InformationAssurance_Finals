import hashlib
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from datetime import datetime


# Hash password using SHA-256
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# SQLite Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expense.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database and migration
db = SQLAlchemy(app)


# Database Models
class User_new(db.Model):
    __tablename__ = 'user_new'

    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(50), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(15), nullable=True)
    birthday = db.Column(db.Date, nullable=True)
    address = db.Column(db.String(200), nullable=True)
    
    # Define the relationship with the transactions table
    transactions = db.relationship('Transaction', backref='user', lazy=True)

class Transaction(db.Model):
    __tablename__ = 'transaction'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign key column to link the transaction with the user
    user_id = db.Column(db.Integer, db.ForeignKey('user_new.id'), nullable=False)


# Create the database and tables (run this once or after changes to models)
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    if 'user_email' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        flash('Please log in to access the dashboard.', 'error')
        return redirect(url_for('login'))

    # Fetch the currently logged-in user
    user = User_new.query.filter_by(email=session['user_email']).first()

    if user:
        # Query transactions for the logged-in user only
        transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.date.desc()).all()
        
        # If no transactions exist for the user, show a welcome message
        if not transactions:
            flash('Welcome to your new account! Start logging transactions.', 'info')

        return render_template('dashboard.html', transactions=transactions, user=user)
    
    flash('User not found.', 'error')
    return redirect(url_for('login'))

@app.route('/user')
def user_profile():
    if 'user_email' not in session:
        flash('Please log in to access your profile.', 'error')
        return redirect(url_for('login'))

    user = User_new.query.filter_by(email=session['user_email']).first()
    
    return render_template('user.html', user=user)

@app.route('/log', methods=['POST'])
def log_transaction():
    if 'user_email' not in session:
        return jsonify({'success': False, 'error': 'Please log in to log a transaction.'})

    description = request.form.get('description', '').strip()
    amount = request.form.get('amount', '').strip()
    type_ = request.form.get('type', '').strip()

    if not description or not amount or not type_:
        return jsonify({'success': False, 'error': 'All fields are required.'})

    try:
        amount = float(amount)
        user = User_new.query.filter_by(email=session['user_email']).first()

        if not user:
            return jsonify({'success': False, 'error': 'User not found.'})

        transaction = Transaction(description=description, amount=amount, type=type_, user_id=user.id)
        db.session.add(transaction)
        db.session.commit()

        return jsonify({
            'success': True,
            'description': description,
            'amount': amount,
            'type': type_,
            'date': transaction.date.strftime('%Y-%m-%d %H:%M:%S')
        })
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid amount.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Fetch the user by email
        user = User_new.query.filter_by(email=email).first()

        # Hash the entered password using SHA-256 for comparison
        hashed_password = hash_password(password)

        if user and user.password == hashed_password:
            session['user_email'] = email
            return redirect(url_for('dashboard'))
        
        flash('Invalid credentials, please try again.', 'error')
        return redirect(url_for('login'))
    return render_template('login.html')

import re
from flask import flash, redirect, render_template, request, url_for
from datetime import datetime


def is_strong_password(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password): 
        return False
    if not re.search(r"[a-z]", password): 
        return False
    if not re.search(r"[0-9]", password):  
        return False
    if not re.search(r"[@$!%*?&]", password): 
        return False
    return True

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        password = request.form['password']
        contact_number = request.form['contact_number']
        birthday = request.form['birthday']
        address = request.form['address']

        # Check if the email already exists
        user = User_new.query.filter_by(email=email).first()
        if user:
            flash('Email already exists. Please use a different one.', 'error')
            return redirect(url_for('register'))

        # Hash the password using bcrypt
        hashed_password = hash_password(password)

        # Create the new user instance
        new_user = User_new(
            firstname=firstname,
            lastname=lastname,
            email=email,
            password=hashed_password,
            contact_number=contact_number,
            birthday=datetime.strptime(birthday, '%Y-%m-%d') if birthday else None,
            address=address
        )
        
        # Add and commit the new user to the database
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')



@app.route('/logout')
def logout():
    session.pop('user_email', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/user-management')
def user_management():
    if 'user_email' not in session:
        flash('Please log in to access the user management.', 'error')
        return redirect(url_for('login'))

    user = User_new.query.filter_by(email=session['user_email']).first()
    if user:
        return render_template('user.html', user=user)
    flash('User not found.', 'error')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
