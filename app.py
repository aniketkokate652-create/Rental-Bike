from flask import Flask, render_template
from flask_migrate import Migrate
import click, os, redis
from flask.cli import with_appcontext

from models import db, User
from auth_bp import auth_bp
from rental_bp import rental_bp
from admin_bp import admin_bp
from werkzeug.security import generate_password_hash

app = Flask(__name__)
# ---------------- REDIS SETUP ----------------
# Checks Render for a REDIS_URL, falls back to localhost for VS Code
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = redis.Redis.from_url(redis_url)

# ---------------- CONFIG ----------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# ---------------- INIT ----------------
db.init_app(app)
migrate = Migrate(app, db)

# ---------------- BLUEPRINTS ----------------
app.register_blueprint(auth_bp)
app.register_blueprint(rental_bp)
app.register_blueprint(admin_bp)

# ---------------- CLI SUPERUSER ----------------
@app.cli.command("createsuperuser")
@with_appcontext
def createsuperuser():
    """Create admin user safely"""
    username = click.prompt("Username")
    email = click.prompt("Email Address")
    password = click.prompt("Password", hide_input=True, confirmation_prompt=True)

    if User.query.filter_by(username=username).first():
        click.echo("❌ User already exists")
        return

    admin = User(
        username=username,
        email=email,
        password=generate_password_hash(password),
        is_admin=True
    )
    db.session.add(admin)
    db.session.commit()
    click.echo("✅ Superuser created")

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
