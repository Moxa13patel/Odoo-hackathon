from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI='sqlite:///stackit.db',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    # Register Blueprints
    from .routes import main
    from .admin import admin_bp
    app.register_blueprint(main)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Login setup
    login_manager.login_view = 'main.login'

    # ✅ User loader for Flask-Login
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
