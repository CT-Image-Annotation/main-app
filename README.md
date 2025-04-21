# Main Repository for CT-Image Annotation

## Setup

To start the project, first set up python environment and requirements.

```bash
conda create -n ct-flask
conda activate ct-flask
conda install pip
pip install -r requirements.txt
```

For AI model, we need its [requirements](https://github.com/bowang-lab/MedSAM) checkpoint as well. The code autodownloads the [model](https://drive.google.com/drive/folders/1ETWmi4AiniJeWOt6HAsYgTjYv_fkgzoN?usp=drive_link) into ```work_dir/MedSAM/medsam_vit_b.pth``` if API endpoint is called. Install the requirements with

```bash
cd app/vendors/MedSAM
pip install -e .
```

Then ensure .env file is correct and

```bash
flask db init
flask db migrate -m "init"
flask db upgrade
flask run
```
