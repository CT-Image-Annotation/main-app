from flask import Blueprint, render_template

bp = Blueprint("editor", __name__)

@bp.route('/<int:dataset_id>')
def index(dataset_id):
    return render_template('editor/index.html', dataset_id=dataset_id)