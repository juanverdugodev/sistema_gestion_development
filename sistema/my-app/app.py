import os
import secrets
from flask import Flask
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Ruta de almacenamiento apuntando al volumen de Docker para vol-app
    app.config['UPLOAD_FOLDER'] = '/storage_datos/storage-files'

    # Crea la carpeta automáticamente si no existe al arrancar la app
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    """Añade cabeceras para que el navegador no guarde en caché 
    páginas protegidas y fuerce la validación con el servidor."""

    @app.after_request
    def add_header(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    from routers.auth import auth
    from routers.main import main

    app.register_blueprint(auth)
    app.register_blueprint(main)

    return app