from flask import Blueprint, jsonify, make_response, request, session

from app.services.DatasetService import DatasetService
from app.services.UserService import UserService
bp = Blueprint("api", __name__)


# USER
@bp.route("/user/create", methods=["POST"])
def createUser(request):
    params = request.form if request.form else request.get_json()
    user = UserService.register(params)
    if not user:
        return {}, 400
    
    return jsonify(user.serialize()), 201


@bp.route("/user/<int:user_id>", methods=["GET"])
def readUser(user_id):
    return jsonify(UserService.read(user_id=user_id).serialize()), 200

@bp.route("/user", methods=["POST"])
def updateUser():
    pass

@bp.route("/user/<int:user_id>", methods=["DELETE"])
def deleteUser(user_id):
    UserService.delete(user_id)
    return jsonify(), 204

@bp.route("/user/<int:user_id>/datasets", methods=["GET"])
def readUserDatasets(user_id):
    return jsonify([d.serialize() for d in DatasetService.read_all(user_id, "user")])

# DATASET
@bp.route("/dataset/create", methods=["POST"])
def createDataset():
    params = request.form if request.form else request.get_json()
    dataset = DatasetService.create(params)
    if not dataset:
        return {}, 400
    
    return jsonify(dataset.serialize()), 201

@bp.route("/dataset/<int:dataset_id>", methods=["GET"])
def readDataset(dataset_id):
    return jsonify(DatasetService.read(dataset_id=dataset_id).serialize()), 200

@bp.route("/dataset", methods=["POST"])
def updateDataset():
    pass

@bp.route("/dataset/<int:dataset_id>", methods=["DELETE"])
def deleteDataset(dataset_id):
    DatasetService.delete(dataset_id)
    return {}, 204

# IMAGE

# ANNOTATION