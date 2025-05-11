from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app, send_from_directory
from app.services.FileService import FileService
from app.services.UserService import UserService
from app.models.User import User
import random
from werkzeug.utils import secure_filename
import os
from datetime import datetime

bp = Blueprint("auth", __name__)

# Inspirational quotes for the doctor profile page
QUOTES = [
    "...let me congratulate you on the choice of calling which offers a combination of intellectual and moral interests found in no other profession.\n- Sir William Olser",
    "Wherever the art of Medicine is loved, there is also a love of Humanity.\n- Hippocrates",
    "I remind my fellows, residents and medical students that what we do is a privilege. People let us into the most intimate aspects of their lives, and they look to us to help guide them through very complex and delicate situations.\n- Shikha Jain, MD",
    "In our job, you will never go home at the end of the day thinking that you haven't done something valuable and important.\n- Suneel Dhand",
    "As a caregiver, you see selfless acts everyday.\n- Dr. Raj Panjabi",
    "[Being a doctor] offers the most complete and constant union of those three qualities which have the greatest charm for pure and active minds – novelty, utility, and charity.\n- Sir James Paget",
    "[As a doctor] people will trust you, confide in you, and appreciate your efforts. You can do amazing things for people if you don't let the system get you down.\n- Wes Fischer, MD",
    "In nothing do men more nearly approach the gods than in giving health to men.\n- Cicero",
    "While the journey seems long and hard at the beginning with perseverance and dedication the rewards at the end last a lifetime.\n- William R. Francis",
    "To solve a difficult problem in medicine, don't study it directly, but rather pursue a curiosity about nature and the rest will follow. Do basic research.\n- Roger Kornberg, PhD",
    "The awe of discovering the human body. The honor of being trusted to give advice. The gratitude for helping someone through a difficult illness. These things never grow old.\n- Danielle Ofri, MD",
    "I always tell my residents to never forget that we have the opportunity to do more good in one day than most people have in a month.\n- Suneel Dhand",
    "I would still 'do it again' despite all the difficulty of training and roadblocks to just practice medicine. Truly is worth it!\n- James A. Bowden, MD",
    "Observation, Reason, Human Understanding, Courage; these make the physician.\n- Martin H. Fischer",
    "Wear the white coat with dignity and pride—it is an honor and privilege to get to serve the public as a physician.\n- Bill H. Warren, MD",
    "Always remember the privilege it is to be a physician.\n- Daniel P. Logan, MD",
    "We practice medicine that our historical ancestors could only dream of, and we have access to amazing treatments and cures for our patients on a daily basis.\n- Suneel Dhand, MD",
    "Medicine really matured me as a person because, as a physician, you're obviously dealing with life and death issues… if you can handle that, you can handle anything.\n- Ken Jeong, MD",
    "People pay the doctor for his trouble; for his kindness they still remain in his debt.\n- Seneca",
    "You [future doctors] are off to an amazing, rewarding and exciting life.\n- Major W. Bradshaw, MD",
    "I remember the feeling of joy, almost to tears, the day I discharged my first patient from the hospital and the tears that I can never hold back during the miracle of birth. That feeling is reward for our hard work here [in medical school] and in years that follow... I can't imagine being a doctor without it... I ask you to recall the vigor and happiness of our youths and then, imagine the beauty of that energy channeled into the care of another human being.\n- John-Paul H. Dedam",
]


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if UserService.login(request.form):
            return redirect(url_for("dashboard.index"))
        flash("", "error")
        
    return render_template('auth/login.html')

@bp.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        if UserService.register(request.form):
            return redirect(url_for("dashboard.index"))
        flash("", "error")
        
    return render_template("auth/register.html")

@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('landing.index'))

@bp.route("/profile", methods=["GET"])
def profile():
    if not session.get('user_id'):
        return redirect(url_for("auth.login"))

    # Fetch the current user
    user = UserService.read(session.get('user_id'))
    if not user:
        session.clear()  # Clear invalid session
        flash("Your session has expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    # Total images owned by this user
    try:
        imageCount = user.resources.filter_by(type="AImage").count()
    except Exception:
        imageCount = len(user.resources)

    # Count all images inside datasets tagged "Done"
    done_count = 0
    # user.datasets is a dynamic relationship; filter_by works here
    for ds in user.datasets.filter_by(status="done"):
        try:
            done_count += ds.resources.count()
        except Exception:
            done_count += len(ds.resources)

    annotationCount = done_count
    pendingCount    = imageCount - done_count

    # Current date & time formatted
    now = datetime.now()
    currentTime = now.strftime("%B %d, %Y %I:%M %p")

    # Pick a random quote
    quote = random.choice(QUOTES)

    profile_photo = FileService.getUserFiles(type="PP")
    if profile_photo:
        profile_photo = profile_photo[0]

    return render_template(
        "auth/profile.html",
        imageCount=imageCount,
        annotationCount=annotationCount,
        pendingCount=pendingCount,
        currentTime=currentTime,
        quote=quote,
        profile_photo = profile_photo,
    )

@bp.route('/profile/edit', methods=['GET','POST'])
def edit_profile():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    user = UserService.read(session['user_id'])

    if request.method == 'POST':
        # 1) Specialty
        specialty = request.form.get('specialty').strip()

        # 2) Photo upload
        photo = request.files.get('photo')
        if photo:
            for old in FileService.getUserFiles(type="PP"):
                FileService.delete(old.id)

            params = {
                "type": "PP",
                "owner_id": user.id,
                "owner_type": "user",
                "file": photo
            }
            resource = FileService.create(params)

        params = {
            "user_id": user.id,
            "specialty": specialty,
        }
        if UserService.update(params):
            flash('Profile updated!', 'success')
        else:
            flash('Failed update!', 'error')

        return redirect(url_for('auth.profile'))

    return render_template('auth/edit_profile.html')