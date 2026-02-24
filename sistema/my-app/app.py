import os
import secrets
from flask import Flask

def create_app():
    app = Flask(__name__)

    app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    from routers.auth import auth
    from routers.main import main

    app.register_blueprint(auth)
    app.register_blueprint(main)

    return app