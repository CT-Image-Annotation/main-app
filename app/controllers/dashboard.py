from flask import Blueprint, render_template, session, redirect, url_for, request, flash, abort
from app.services.DatasetService import DatasetService
from app.services.FileService import FileService

bp = Blueprint("dashboard", __name__, url_prefix='/dashboard')

@bp.route('/')
def index():
    if not session.get('user_id'):
        return redirect(url_for("auth.login"))

    user_id = session['user_id']
    # Fetch all datasets belonging to the user
    all_datasets = DatasetService.list_for_user(user_id)

    # Partition into To Do vs Done
    todo_datasets = [ds for ds in all_datasets if ds.tags == 'To Do']
    done_datasets = [ds for ds in all_datasets if ds.tags == 'Done']

    return render_template(
        'dashboard/index.html',
        todo_datasets=todo_datasets,
        done_datasets=done_datasets
    )

@bp.route('/datasets/<int:ds_id>/upload', methods=['POST'])
def upload_to_dataset(ds_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    ds = DatasetService.read_for_user(ds_id, user_id)
    if not ds:
        abort(403)
    if 'files' not in request.files:
        flash('No files selected', 'error')
        return redirect(url_for('dashboard.index'))
    files = request.files.getlist('files')
    if not files or all(file.filename == '' for file in files):
        flash('No files selected', 'error')
        return redirect(url_for('dashboard.index'))
    success_count = 0
    error_messages = []
    for f in files:
        if f and f.filename:
            try:
                FileService.upload(f, type='AImage', dataset_id=ds_id)
                success_count += 1
            except ValueError as e:
                error_messages.append(f"{f.filename}: {str(e)}")
            except Exception as e:
                error_messages.append(f"{f.filename}: An error occurred during upload")
    if success_count > 0:
        flash(f"Successfully uploaded {success_count} files.", 'success')
    if error_messages:
        flash('\n'.join(error_messages), 'error')
    return redirect(url_for('dashboard.index'))
