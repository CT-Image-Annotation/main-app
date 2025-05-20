# Main Repository for CT-Image Annotation

## Setup

To start the project, first set up python environment and requirements.

```bash
conda create -n ct-flask
conda activate ct-flask
conda install pip
pip install -r requirements.txt
```

MEDSAM-2 installation

First, update the environment with MEDSAM-2 requirements
```bash
conda env update \
  --name ct-flask \
  --file app/vendors/Medical-SAM2/environment.yml
```

Secondly, download the weights
```bash
cd app/vendors/Medical-SAM2/checkpoints
bash  download_ckpts.sh
```

Done with medsam-2 installation

Go Back to /main-app
```bash
cd ../../../../
```

Initialize flask (REMOVES PREVIOUS DATABASES and UPLOADS)
```bash 
bash setup.sh
```

Run Flask
```bash
flask run
```

Your APP should be running.



LEGACY

Init Flask

```bash
flask db init
flask db migrate -m "init"
flask db upgrade
flask run
```


THIS IS FOR OLDER MEDSAM
~For AI model, we need its [requirements](https://github.com/bowang-lab/MedSAM) checkpoint as well. The code autodownloads the [model](https://drive.google.com/drive/folders/1ETWmi4AiniJeWOt6HAsYgTjYv_fkgzoN?usp=drive_link) into ```work_dir/MedSAM/medsam_vit_b.pth``` if API endpoint is called. Install the requirements with

```bash
cd app/vendors/MedSAM
pip install -e .
```
~