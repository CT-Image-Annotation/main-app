
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.services.UserService import UserService
bp = Blueprint("auth", __name__)

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if UserService.login(request.form):
            return redirect(url_for("dashboard.index"))
        else:
            flash("No", "error")
        
    return render_template('auth/login.html')

@bp.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        if UserService.register(request.form):
            return redirect(url_for("dashboard.index"))
        
        flash("No register", "error")
    
    return render_template("auth/register.html")

@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('landing.index'))