from flask import Blueprint, render_template, redirect, url_for
import redis
from models import db, Bike

rental_bp = Blueprint('rental', __name__)

# Redis Connection with Safety
try:
    r = redis.Redis(host='localhost', port=6379, decode_responses=True, socket_connect_timeout=1)
    r.ping() # Check if alive
except:
    r = None 

@rental_bp.route('/bikes')
def list_bikes():
    available_bikes = Bike.query.filter_by(is_available=True).all()
    return render_template('bikes.html', bikes=available_bikes)

@rental_bp.route('/rent/<int:bike_id>', methods=['POST'])
def rent_bike(bike_id):
    bike = Bike.query.get(bike_id)
    if bike:
        bike.is_available = False
        db.session.commit()
    return redirect(url_for('rental.list_bikes'))

@rental_bp.app_context_processor
def inject_offer():
    offer = "New Users get 20% off!"
    if r:
        try:
            cached_offer = r.get("flash_sale")
            if not cached_offer:
                r.setex("flash_sale", 60, "FLASH SALE: 50% OFF TODAY!")
                cached_offer = "FLASH SALE: 50% OFF TODAY!"
            offer = cached_offer
        except:
            pass
    return dict(offer=offer)