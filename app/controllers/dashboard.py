from flask import Blueprint, render_template, session, redirect, url_for
from app.services.DatasetService import DatasetService

bp = Blueprint("dashboard", __name__)

@bp.route('/')
def index():
    if not session.get('user_id'):
        return redirect(url_for("auth.login"))

    user_id = session['user_id']
    # Fetch all datasets belonging to the user
    all_datasets = DatasetService.read_all(user_id, "user")

    # Partition into To Do vs Done
    todo_datasets = [ds for ds in all_datasets if ds.status == 'todo']
    done_datasets = [ds for ds in all_datasets if ds.status == 'done']

    return render_template(
        'dashboard/index.html',
        todo_datasets=todo_datasets,
        done_datasets=done_datasets
    )
