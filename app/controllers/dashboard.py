from flask import Blueprint, render_template, session, request, redirect, url_for

bp = Blueprint("dashboard", __name__)

@bp.route('/')
def index():
    if not session.get('user_id'):
        return redirect(url_for("auth.login"))
    return render_template('dashboard/index.html')