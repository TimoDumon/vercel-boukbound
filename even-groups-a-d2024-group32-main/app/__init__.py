from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from .config import Config
from werkzeug.security import generate_password_hash, check_password_hash


# Initialiseer de database
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialiseert CSRF-protectie
    csrf.init_app(app)

    # Initialiseer de database met de applicatie
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialiseer de login manager
    login_manager.init_app(app)
    
    # Stel in hoe gebruikers geladen moeten worden
    @login_manager.user_loader
    def load_user(user_id):
        # Verplaats de User import naar binnen in de functie om een circulaire import te vermijden
        from .models import User
        return User.query.get(int(user_id))

    # Registreer de blueprint
    from .routes import main
    app.register_blueprint(main)

    return app
