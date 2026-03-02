from flask import Flask, render_template
from flask_migrate import Migrate
import click, os, redis
from flask.cli import with_appcontext
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

# 1. Import db and User first
from models import db, User

app = Flask(__name__)

# ---------------- CONFIG ----------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# ---------------- INIT ----------------
db.init_app(app)
migrate = Migrate(app, db)

# 2. Setup Login Manager before Blueprints
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 3. Import Blueprints HERE (Delayed Import to prevent Circular Errors)
from auth_bp import auth_bp
from rental_bp import rental_bp
from admin_bp import admin_bp

# ---------------- REDIS SETUP ----------------
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
try:
    redis_client = redis.Redis.from_url(redis_url)
except Exception as e:
    print(f"Redis not connected: {e}")

# ---------------- BLUEPRINTS ----------------
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(rental_bp, url_prefix='/rental')

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
    # Ensure upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)