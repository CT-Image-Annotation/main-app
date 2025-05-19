import os
from flask import Blueprint, current_app, jsonify, request, send_file, send_from_directory, session, Response
from PIL import Image
from app.services.AnnotationService import AnnotationService
from app.services.BoundingBoxSegmentationService import BoundingBoxSegmentationService
from app.services.DatasetService import DatasetService
from app.services.FileService import FileService
from app.services.UserService import UserService
import io
bp = Blueprint("api", __name__)


@bp.route("/ai", methods=["GET"])
def ai():
    resource_id = request.args.get("resource_id", type=int)
    xmin = request.args.get("xmin", type=int)
    ymin = request.args.get("ymin", type=int)
    xmax = request.args.get("xmax", type=int)
    ymax = request.args.get("ymax", type=int)

    if None in [resource_id, xmin, ymin, xmax, ymax]:
        return {"error": "Missing parameters"}, 400
    
    resource = FileService.find(resource_id)

    image_buffer = FileService.load(resource.path)

    box_coords = [[xmin, ymin, xmax, ymax]] #[[75, 75, 240, 420]]

    pil_image = Image.fromarray(BoundingBoxSegmentationService.segmentBox(image_buffer, box_coords))
    
    # Save the image to a BytesIO object in PNG format
    img_io = io.BytesIO()
    pil_image.save(img_io, 'PNG')
    img_io.seek(0)  # Go to the beginning of the BytesIO buffer
    
    # Return the image as a response
    return Response(img_io, mimetype='image/png')

    return 

# USER
@bp.route("/user/create", methods=["POST"])
def createUser():
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
@bp.route("/image/create", methods=["POST"])
def createImage():
    params = dict(request.form) if request.form else request.get_json()
    params["file"] = request.files.get("file")
    image = FileService.create(params)
    if not image:
        return {}, 400
    
    return jsonify(image.serialize()), 201

@bp.route("/image/<int:image_id>", methods=["GET"])
def readImage(image_id):
    return jsonify(FileService.read(resource_id=image_id).serialize()), 200

@bp.route("/image", methods=["POST"])
def updateImage():
    pass

@bp.route("/image/<int:image_id>", methods=["DELETE"])
def deleteImage(image_id):
    FileService.delete(image_id)
    return {}, 204

# ANNOTATION
@bp.route("/annotation/create", methods=["POST"])
def createAnnotation():
    params = dict(request.form) if request.form else request.get_json()
    params["file"] = request.files.get("file")
    annotation = AnnotationService.create(params)
    if not annotation:
        return {},400
    
    return jsonify(annotation.serialize()), 201

@bp.route("/annotation/<int:annotation_id>", methods=["GET"])
def readAnnotation(annotation_id):
    return jsonify(AnnotationService.read(annotation_id=annotation_id).serialize()), 200

@bp.route("/annotation", methods=["POST"])
def updateAnnotation():
    pass

@bp.route("/annotation/<int:annotation_id>", methods=["DELETE"])
def deleteAnnotation(annotation_id):
    FileService.delete(annotation_id)
    return {}, 204

@bp.route("/annotation/load-last/<int:resource_id>")
def downloadLastAnnotation(resource_id):
    annotation_resource = AnnotationService.read_last(resource_id)
    if not annotation_resource:
        return {},404

    return send_file(os.path.join(current_app.config['UPLOAD_FOLDER'],annotation_resource.file.path))