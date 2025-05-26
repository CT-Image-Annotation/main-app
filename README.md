# Main Repository for CT-Image Annotation

## Setup

### Local
For local development, we need conda, and local database.

```bash
conda create -n ct-flask
conda activate ct-flask
conda install pip
pip install -r requirements.txt
```

Then run `sh setup.sh` or

```bash
flask db init
flask db migrate -m "init"
flask db upgrade
flask run
```

### Production
Install docker, docker compose, then

`docker compose up --build`