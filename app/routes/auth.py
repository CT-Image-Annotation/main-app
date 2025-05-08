from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.services.UserService import UserService

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = UserService.login(username, password)
        if user:
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')
        
        # Attempt registration
        if UserService.register(username, password):
            return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('auth.login')) 