from flask import Flask

from app.auth import auth_bp
from app.config import Config
from app.extensions import db, login_manager
from app.views import views_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)

    return app
