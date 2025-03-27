from flask import Blueprint, jsonify, render_template, session, request, redirect, url_for

from app.services.DatasetService import DatasetService

bp = Blueprint("datasets", __name__)

@bp.route('/')
def index():
    if not session.get('user_id'):
        return redirect(url_for("auth.login"))
    user_id = session.get('user_id')
    datasets = DatasetService.read_all(user_id, "user")
    print(datasets)
    return render_template('datasets/index.html', datasets=datasets)

@bp.route('/create')
def create():

    # if not session.get('user_id'):
    #     return redirect(url_for("auth.login"))
    # user_id = session.get('user_id')
    name = request.args.get('name')

    DatasetService.create(name, 1, "user")
    return redirect(url_for("datasets.index"))

@bp.route('/<int:dataset_id>/resources', methods=['GET'])
def api_dataset_resources(dataset_id):

    return jsonify({'resources':[{
        'name': resource.name,
        'path': url_for("uploads.download", path=resource.path),
    } for resource in DatasetService.read(dataset_id).resources]})