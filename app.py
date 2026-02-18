from flask import Flask, render_template
from models import db, Bike
from auth_bp import auth_bp # Now matches filename
from rental_bp import rental_bp
import click
from flask.cli import with_appcontext
from models import db, User
from admin_bp import admin_bp
import os


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
app.config['SECRET_KEY'] = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
@app.cli.command("createsuperuser")
@with_appcontext
def createsuperuser():
    """Create a new admin user via terminal."""
    username = click.prompt("Username")
    password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
    
    # Check if user exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        print(f"Error: User {username} already exists.")
        return

    # Create the admin user
    new_admin = User(username=username, password=password, is_admin=True)
    db.session.add(new_admin)
    db.session.commit()
    print(f"Superuser '{username}' created successfully!")
db.init_app(app)

app.register_blueprint(auth_bp)
app.register_blueprint(rental_bp)
app.register_blueprint(admin_bp)

with app.app_context():
    db.create_all()

    if not Bike.query.first():
        bikes = [
            Bike(
                model_name="Mountain Bike",
                price_per_day=500,
                image_file=None,
                is_available=True
            ),
            Bike(
                model_name="City Bike",
                price_per_day=400,
                image_file=None,
                is_available=True
            )
        ]
        db.session.add_all(bikes)
        db.session.commit()


@app.route('/')
def home():
    return render_template('index.html')



if __name__ == '__main__':
    # Use 0.0.0.0 to make it accessible on your local network if needed
    app.run(debug=True)

