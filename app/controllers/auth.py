from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app, send_from_directory
from app.services.UserService import UserService
import random
from werkzeug.utils import secure_filename
import os
from datetime import datetime

bp = Blueprint("auth", __name__)

# Inspirational quotes for the doctor profile page
QUOTES = [
    "...let me congratulate you on the choice of calling which offers a combination of intellectual and moral interests found in no other profession.\n- Sir William Olser",
    "Wherever the art of Medicine is loved, there is also a love of Humanity.\n- Hippocrates",
    "I remind my fellows, residents and medical students that what we do is a privilege. People let us into the most intimate aspects of their lives, and they look to us to help guide them through very complex and delicate situations.\n- Shikha Jain, MD via KevinMD",
    "In our job, you will never go home at the end of the day thinking that you haven’t done something valuable and important.\n- Suneel Dhand via Doc Thinx",
    "As a caregiver, you see selfless acts everyday.\n- Dr. Raj Panjabi via The Huffington Post",
    "[Being a doctor] offers the most complete and constant union of those three qualities which have the greatest charm for pure and active minds – novelty, utility, and charity.\n- Sir James Paget",
    "[As a doctor] people will trust you, confide in you, and appreciate your efforts. You can do amazing things for people if you don’t let the system get you down.\n- Wes Fischer, MD via Kevin MD",
    "In nothing do men more nearly approach the gods than in giving health to men.\n- Cicero",
    "While the journey seems long and hard at the beginning with perseverance and dedication the rewards at the end last a lifetime.\n- William R. Francis via Baylor College of Medicine",
    "To solve a difficult problem in medicine, don't study it directly, but rather pursue a curiosity about nature and the rest will follow. Do basic research.\n- Roger Kornberg, PhD via Stanford School of Medicine & Becker's Hospital Review",
    "The awe of discovering the human body. The honor of being trusted to give advice. The gratitude for helping someone through a difficult illness. These things never grow old.\n- Danielle Ofri, MD via The New York Times",
    "I always tell my residents to never forget that we have the opportunity to do more good in one day than most people have in a month.\n- Suneel Dhand via Doc Thinx",
    "I would still ‘do it again’ despite all the difficulty of training and roadblocks to just practice medicine. Truly is worth it!\n- James A. Bowden, MD via Baylor College of Medicine",
    "Observation, Reason, Human Understanding, Courage; these make the physician.\n- Martin H. Fischer",
    "Wear the white coat with dignity and pride—it is an honor and privilege to get to serve the public as a physician.\n- Bill H. Warren, MD via Baylor College of Medicine",
    "Always remember the privilege it is to be a physician.\n- Daniel P. Logan, MD via Baylor College of Medicine",
    "We practice medicine that our historical ancestors could only dream of, and we have access to amazing treatments and cures for our patients on a daily basis.\n- Suneel Dhand, MD via KevinMD",
    "Medicine really matured me as a person because, as a physician, you're obviously dealing with life and death issues… if you can handle that, you can handle anything.\n- Ken Jeong, MD via The Aquarian",
    "People pay the doctor for his trouble; for his kindness they still remain in his debt.\n- Seneca",
    "You [future doctors] are off to an amazing, rewarding and exciting life.\n- Major W. Bradshaw, MD via Baylor College of Medicine",
    "I remember the feeling of joy, almost to tears, the day I discharged my first patient from the hospital and the tears that I can never hold back during the miracle of birth. That feeling is reward for our hard work here [in medical school] and in years that follow... I can't imagine being a doctor without it... I ask you to recall the vigor and happiness of our youths and then, imagine the beauty of that energy channeled into the care of another human being.\n- John-Paul H. Dedam via Darmouth",
]


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if UserService.login(request.form):
            return redirect(url_for("dashboard.index"))
        else:
            flash("No", "error")
    return render_template('auth/login.html')

@bp.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        if UserService.register(request.form):
            return redirect(url_for("dashboard.index"))
        flash("No register", "error")
    return render_template("auth/register.html")

@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('landing.index'))

@bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@bp.route("/profile", methods=["GET"])
def profile():
    if not session.get('user_id'):
        return redirect(url_for("auth.login"))

    # Fetch the current user
    user = UserService.read(session.get('user_id'))

    # Counts for images and annotations (dynamic or list relationships)
    try:
        imageCount = user.resources.count()
    except Exception:
        imageCount = len(user.resources)
    try:
        annotationCount = user.annotations.count()
    except Exception:
        annotationCount = len(user.annotations)
    pendingCount = imageCount - annotationCount

    # Current date & time formatted
    now = datetime.now()
    currentTime = now.strftime("%B %d, %Y %I:%M %p")

    # Pick a random quote
    quote = random.choice(QUOTES)

    return render_template(
        "auth/profile.html",
        user=user,
        imageCount=imageCount,
        annotationCount=annotationCount,
        pendingCount=pendingCount,
        currentTime=currentTime,
        quote=quote
    )

@bp.route('/profile/edit', methods=['GET','POST'])
def edit_profile():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))

    user = UserService.read(session['user_id'])

    if request.method == 'POST':
        # 1) Specialty
        user.specialty = request.form.get('specialty', '').strip()

        # 2) Photo upload
        photo = request.files.get('photo')
        if photo and photo.filename:
            fname = secure_filename(photo.filename)
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], fname)
            photo.save(save_path)
            user.profile_photo = fname

        UserService.update(user)   # you’ll need an update() method in UserService
        flash('Profile updated!', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/edit_profile.html', user=user)