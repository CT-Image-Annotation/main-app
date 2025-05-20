from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app, send_from_directory
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
        else:
            flash("No", "error")
    return render_template('auth/login.html')

@bp.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Validate required fields
        if not username or not password:
            flash("Username and password are required", "error")
            return render_template("auth/register.html")
            
        # Check if username is already taken
        if User.query.filter_by(username=username).first():
            flash("Username is already taken. Please choose a different username.", "error")
            return render_template("auth/register.html")
            
        # Attempt registration
        if UserService.register(request.form):
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("auth.profile"))
        else:
            flash("Registration failed. Please try again.", "error")
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
    if not user:
        session.clear()  # Clear invalid session
        flash("Your session has expired. Please log in again.", "error")
        return redirect(url_for("auth.login"))

    # Total images owned by this user
    try:
        imageCount = user.resources.count()
    except Exception:
        imageCount = len(user.resources)

    # Count all images inside datasets tagged "Done"
    done_count = 0
    # user.datasets is a dynamic relationship; filter_by works here
    for ds in user.datasets.filter_by(tags="Done"):
        try:
            done_count += ds.files.count()
        except Exception:
            done_count += len(ds.files)

    annotationCount = done_count
    pendingCount    = imageCount - done_count

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

        UserService.update(user)   # you'll need an update() method in UserService
        flash('Profile updated!', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/edit_profile.html', user=user)