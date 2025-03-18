# Project Structure

my_flask_app/
├── app.py
├── config.py
├── routes.py
└── image_processing.py

main.ipynb – The main entry point that creates the Flask app, registers blueprints, and runs the server.
config.py – Contains configuration variables (like UPLOAD_FOLDER and allowed file extensions).
routes.py – Defines the view functions and routes using a Blueprint.
image_processing.py – Contains helper functions for image processing (e.g., allowed_file, image thresholding, etc.).

