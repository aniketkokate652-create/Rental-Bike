from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from datetime import datetime
import redis
from models import db, Bike, Booking, User

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

# ---------------- ROUTES ----------------
@rental_bp.route("/bikes", methods=["GET", "POST"])
def list_bikes():
    available_bikes = Bike.query.filter_by(is_available=True).all()
    return render_template("bikes.html", bikes=available_bikes)

# 👇 THIS WAS LIKELY MISSING 👇
@rental_bp.route("/rent/<int:bike_id>", methods=["POST"])
def rent_bike(bike_id):
    if not session.get("user_id"):
        flash("Please login to rent a bike.", "warning")
        return redirect(url_for("auth.login"))
    return redirect(url_for("rental.user_info", bike_id=bike_id))

@rental_bp.route("/rent/<int:bike_id>/userinfo", methods=["GET", "POST"])
def user_info(bike_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    # Fetch both the bike AND the logged-in user from the database
    bike = Bike.query.get_or_404(bike_id)
    user = User.query.get(user_id) 

    if request.method == "POST":
        # The form was submitted successfully, move to payment
        return redirect(url_for("rental.payment", bike_id=bike_id))

    # Send the user object to the template so it can display their details
    return render_template("user_info.html", bike=bike, user=user)

@rental_bp.route("/payment/<int:bike_id>", methods=["GET", "POST"])
def payment(bike_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    bike = Bike.query.get_or_404(bike_id)
    
    if request.method == "POST":
        booking = Booking(
            user_id=session["user_id"],
            bike_id=bike.id,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
            total_price=bike.price_per_day,
            payment_method=request.form.get("payment_method", "Credit Card"),
            payment_status="SUCCESS"
        )
        bike.is_available = False   # Mark as rented
        db.session.add(booking)
        db.session.commit()

        return render_template("payment_success.html", bike=bike)

    return render_template("payment.html", bike=bike)

@rental_bp.route("/my-bookings")
def my_bookings():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))
    bookings = Booking.query.filter_by(user_id=session["user_id"]).all()
    return render_template("my_bookings.html", bookings=bookings)