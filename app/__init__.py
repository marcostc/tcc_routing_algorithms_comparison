# proj/app/__init__.py

from flask import Flask
from app.routes.routes import main_blueprint

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'sua_chave_secreta'  # Necessário para segurança do Flask-WTF

    app.register_blueprint(main_blueprint)

    return app
