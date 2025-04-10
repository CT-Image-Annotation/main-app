
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

@bp.route("/profile", methods=["GET"])
def profile():
    if not session.get('user_id'):
        return redirect(url_for("auth.login"))
    
    user = UserService.read(session.get('user_id'))
    imageCount = user.resources.count()
    return render_template("auth/profile.html", user=user, imageCount = imageCount)