from flask import Blueprint, jsonify, make_response, request

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

# DATASET
@bp.route("/dataset/create", methods=["POST"])
def createDataset():
    pass

@bp.route("/dataset", methods=["GET"])
def readDataset():
    pass

@bp.route("/dataset", methods=["POST"])
def updateDataset():
    pass

@bp.route("/dataset", methods=["DELETE"])
def deleteDataset():
    pass

# IMAGE

# ANNOTATION