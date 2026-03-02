from flask import Blueprint, render_template, redirect, url_for, request, session, flash, jsonify
from datetime import datetime
import redis
import os
from werkzeug.utils import secure_filename

# Break circular import by importing from models directly
from models import db, Bike, Booking, User, Experience 
from flask_login import login_required, current_user

rental_bp = Blueprint("rental", __name__)

# ---------------- REDIS (SAFE / OPTIONAL) ----------------
try:
    r = redis.Redis(host="localhost", port=6379, decode_responses=True, socket_connect_timeout=1)
    r.ping()
except Exception:
    r = None

# ---------------- GLOBAL OFFER INJECT ----------------
@rental_bp.app_context_processor
def inject_offer():
    offer = "New Users get 20% off!"
    if r:
        try:
            cached_offer = r.get("flash_sale")
            if cached_offer:
                offer = cached_offer
        except Exception:
            pass
    return {"offer": offer}

# ---------------- RENTAL WORKFLOW ROUTES ----------------

@rental_bp.route("/bikes", methods=["GET", "POST"])
def list_bikes():
    available_bikes = Bike.query.filter_by(is_available=True).all()
    return render_template("bikes.html", bikes=available_bikes)

@rental_bp.route("/rent/<int:bike_id>", methods=["POST"])
def rent_bike(bike_id):
    # 1. Check if user is logged in using Flask-Login
    if current_user.is_authenticated:
        # If logged in, go straight to User Info
        return redirect(url_for("rental.user_info", bike_id=bike_id))
    
    # 2. If NOT logged in, show a message and go to Login
    flash("Please login to continue your booking.", "info")
    return redirect(url_for("auth.login"))

@rental_bp.route("/rent/<int:bike_id>/userinfo", methods=["GET", "POST"])
@login_required
def user_info(bike_id):
    bike = Bike.query.get_or_404(bike_id)
    user = current_user
    
    if request.method == "POST":
        # 1. Capture the dates from the form
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        phone = request.form.get('phone')

        # 2. Store them in the session for the Payment page
        session['rental_start'] = start_date
        session['rental_end'] = end_date
        session['user_phone'] = phone

        return redirect(url_for("rental.payment", bike_id=bike_id))
        
    return render_template("user_info.html", bike=bike, user=user)

@rental_bp.route("/rent/<int:bike_id>/payment", methods=["GET", "POST"])
@login_required
def payment(bike_id):
    bike = Bike.query.get_or_404(bike_id)
    
    start_str = session.get('rental_start')
    end_str = session.get('rental_end')
    
    if not start_str or not end_str:
        flash("Please select your rental dates first.", "warning")
        return redirect(url_for('rental.user_info', bike_id=bike_id))

    # Convert strings to Python objects to calculate price
    start_date = datetime.strptime(start_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_str, '%Y-%m-%d')
    
    days = (end_date - start_date).days
    if days <= 0: days = 1
    
    raw_price = days * bike.price_per_day
    total_price = raw_price * 0.80 # 20% OFF applied here

    if request.method == "POST":
        new_booking = Booking(
            user_id=current_user.id,
            bike_id=bike.id,
            start_date=start_date,
            end_date=end_date,
            total_price=total_price,
            payment_method=request.form.get('payment_method', 'UPI'),
            payment_status="SUCCESS"
        )
        
        # Update Bike status
        bike.is_available = False
        db.session.add(new_booking)
        db.session.commit()

        # Clear dates from session
        session.pop('rental_start', None)
        session.pop('rental_end', None)

        flash(f"Payment Successful! You saved {raw_price * 0.20}!", "success")
        # Now the template will know what 'bike' is
        return render_template("payment_success.html", booking=new_booking, bike=bike)

    return render_template("payment.html", bike=bike, total_price=total_price, days=days, original_price=raw_price)

@rental_bp.route("/my-bookings")
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template("my_bookings.html", bookings=bookings)

# ---------------- SEARCH API ----------------

@rental_bp.route('/api/suggest_bikes')
def suggest_bikes():
    query = request.args.get('q', '').lower()
    if len(query) < 2:
        return jsonify([])

    # Fixed: Uses model_name instead of name to match your database
    results = Bike.query.filter(Bike.model_name.ilike(f'%{query}%')).limit(5).all()
    bike_list = [bike.model_name for bike in results]
    return jsonify(bike_list)

# ---------------- RIDING STORIES (SOCIAL MEDIA) ----------------

@rental_bp.route('/experiences')
def experiences():
    all_stories = Experience.query.order_by(Experience.date_posted.desc()).all()
    return render_template('experiences.html', experiences=all_stories)

@rental_bp.route('/upload_experience', methods=['POST'])
@login_required
def upload_experience():
    if 'image' not in request.files:
        flash('No image selected', 'danger')
        return redirect(request.url)
    
    file = request.files['image']
    caption = request.form.get('caption')

    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(request.url)

    if file:
        filename = secure_filename(file.filename)
        # Ensure 'static/uploads' exists in your app.py folder
        upload_path = os.path.join('static/uploads', filename)
        file.save(upload_path)

        new_story = Experience(
            image_file=filename,
            caption=caption,
            user_id=current_user.id
        )
        db.session.add(new_story)
        db.session.commit()
        
        flash('Your story has been shared!', 'success')
        return redirect(url_for('rental.experiences'))

@rental_bp.route('/delete_experience/<int:exp_id>', methods=['POST'])
@login_required
def delete_experience(exp_id):
    story = Experience.query.get_or_404(exp_id)
    
    if story.user_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('rental.experiences'))

    try:
        image_path = os.path.join('static/uploads', story.image_file)
        if os.path.exists(image_path):
            os.remove(image_path)
            
        db.session.delete(story)
        db.session.commit()
        flash("Story deleted.", "success")
    except Exception:
        db.session.rollback()
        flash("Error during deletion.", "danger")

    return redirect(url_for('rental.experiences'))