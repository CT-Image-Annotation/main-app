import os
from flask import (
    Blueprint, current_app, render_template, send_from_directory,
    request, redirect, session, url_for, flash, abort
)
from werkzeug.utils import secure_filename

from app.controllers.processing import FILTER_NAMES
from app.services.FileService import FileService
from app.services.DatasetService import DatasetService

bp = Blueprint('uploads', __name__, url_prefix='/uploads')

@bp.route('/')
def root():
    return redirect(url_for('uploads.datasets_index'))

@bp.route('/datasets', methods=['GET', 'POST'])
def datasets_index():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    if request.method == 'POST':
        # Create the dataset first
        ds = DatasetService.create(request.form, user_id)
        flash('Dataset created!', 'success')
        
        # Handle file uploads if any
        if 'files' in request.files:
            files = request.files.getlist('files')
            if files and not all(file.filename == '' for file in files):
                success_count = 0
                error_messages = []
                
                for f in files:
                    if f and f.filename:
                        try:
                            FileService.upload(f, type='AImage', dataset_id=ds.id)
                            success_count += 1
                        except ValueError as e:
                            error_messages.append(f"{f.filename}: {str(e)}")
                        except Exception as e:
                            error_messages.append(f"{f.filename}: An error occurred during upload")
                
                if success_count > 0:
                    flash(f"Successfully uploaded {success_count} files.", 'success')
                if error_messages:
                    flash('\n'.join(error_messages), 'error')
        
        return redirect(url_for('uploads.datasets_index'))
    
    datasets = DatasetService.list_for_user(user_id)
    from collections import defaultdict
    grouped = defaultdict(list)
    for ds in datasets:
        # Load files for each dataset
        ds.files = FileService.getUserFiles(type='AImage', dataset_id=ds.id)
        key = (ds.patient_id, ds.patient_name)
        grouped[key].append(ds)
    grouped_datasets = [
        {'patient_id': pid, 'patient_name': pname, 'datasets': dsets}
        for (pid, pname), dsets in grouped.items()
    ]
    return render_template('uploads/index.html', grouped_datasets=grouped_datasets)

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
        return redirect(url_for('uploads.dataset_detail', ds_id=ds_id))
    
    files = request.files.getlist('files')
    if not files or all(file.filename == '' for file in files):
        flash('No files selected', 'error')
        return redirect(url_for('uploads.dataset_detail', ds_id=ds_id))
    
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
    
    return redirect(url_for('uploads.dataset_detail', ds_id=ds_id))

@bp.route('/datasets/<int:ds_id>/delete', methods=['POST'])
def delete_dataset(ds_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    if not DatasetService.delete_for_user(ds_id, user_id):
        abort(403)
    flash('Dataset deleted.', 'info')
    return redirect(url_for('uploads.datasets_index'))

@bp.route('/files/<int:file_id>/delete', methods=['POST'])
def delete_file(file_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    file = FileService.read(file_id)
    if not file or file.dataset_id is None or file.dataset.owner_id != session['user_id']:
        abort(403)
    FileService.delete(file_id)
    flash('File deleted.', 'info')
    return redirect(url_for('uploads.datasets_index'))

@bp.route('/<int:ds_id>/<filename>')
def serve_dataset_file(ds_id, filename):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    ds = DatasetService.read_for_user(ds_id, session['user_id'])
    if not ds:
        abort(403)
    directory = os.path.join(current_app.config['UPLOAD_FOLDER'], str(ds_id))
    return send_from_directory(directory, filename)

@bp.route('/datasets/<int:ds_id>', methods=['GET'])
def dataset_detail(ds_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    ds = DatasetService.read_for_user(ds_id, user_id)
    if not ds:
        abort(403)

    # load all files in this dataset
    files = FileService.getUserFiles(type='AImage', dataset_id=ds_id)

    return render_template(
        'uploads/dataset_detail.html',
        dataset=ds,
        files=files,
        filter_names=FILTER_NAMES,
        processes=session.get(f'batch_{ds_id}_processes', [])
    )

@bp.route('/datasets/<int:ds_id>/edit', methods=['GET','POST'])
def edit_dataset(ds_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    user_id = session['user_id']

    # ensure this dataset really belongs to the current user
    ds = DatasetService.read_for_user(ds_id, user_id)
    if not ds:
        abort(403)

    if request.method == 'POST':
        # Update dataset information
        updated = DatasetService.update_for_user(ds_id, user_id, request.form)
        if updated:
            # Handle file uploads if any
            if 'files' in request.files:
                files = request.files.getlist('files')
                if files and not all(file.filename == '' for file in files):
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
            
            flash('Dataset updated!', 'success')
            return redirect(url_for('uploads.datasets_index'))
        flash('Could not update dataset.', 'error')

    # Load files for the dataset
    ds.files = FileService.getUserFiles(type='AImage', dataset_id=ds_id)
    return render_template('uploads/edit_dataset.html', dataset=ds)