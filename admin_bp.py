from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from werkzeug.utils import secure_filename
import os
import redis
from models import db, Bike

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Redis connection
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

UPLOAD_FOLDER = 'static/uploads'


@admin_bp.route('/dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('auth.login'))

    bikes = Bike.query.all()
    total_bikes = len(bikes)
    available_bikes = Bike.query.filter_by(is_available=True).count()
    
    # Active rentals = bikes not available
    active_rentals = Bike.query.filter_by(is_available=False).count()

    current_offer = r.get("flash_sale") or "No active offer"

    return render_template(
        'dashboard.html',
        bikes=bikes,
        total_bikes=total_bikes,
        available_bikes=available_bikes,
        active_rentals=active_rentals,
        offer=current_offer
    )


@admin_bp.route('/add-bike', methods=['POST'])
def add_bike():
    if not session.get('is_admin'):
        return redirect(url_for('auth.login'))

    model_name = request.form['model_name']
    price = request.form['price']
    image = request.files.get('image')

    filename = None
    if image and image.filename != "":
        filename = secure_filename(image.filename)
        image.save(os.path.join(UPLOAD_FOLDER, filename))

    new_bike = Bike(
        model_name=model_name,
        price_per_day=price,
        image_file=filename
    )

    db.session.add(new_bike)
    db.session.commit()

    flash("Bike added successfully!", "success")
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/update-offer', methods=['POST'])
def update_offer():
    if not session.get('is_admin'):
        return redirect(url_for('auth.login'))

    offer_text = request.form['offer']
    r.setex("flash_sale", 3600, offer_text)

    flash("Offer updated!", "success")
    return redirect(url_for('admin.admin_dashboard'))
# Mark bike as AVAILABLE
@admin_bp.route('/bike/make-available/<int:bike_id>', methods=['POST'])
def make_bike_available(bike_id):
    if not session.get('is_admin'):
        abort(403)

    bike = Bike.query.get_or_404(bike_id)
    bike.is_available = True

    db.session.commit()
    flash("Bike marked as available", "success")

    return redirect(url_for('admin.admin_dashboard'))