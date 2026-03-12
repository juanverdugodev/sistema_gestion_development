import mysql.connector
import logging
from mysql.connector import Error
import os

logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        # La versión 9.6.0 de mysql connector -python maneja la autenticación de MySQL 8 automáticamente
        connection = mysql.connector.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'app_user'),
            password=os.environ.get('DB_PASSWORD', 'App@p4ssw0rd26'),
            database=os.environ.get('DB_NAME', 'sistema_gestion_db'),
            port=int(os.environ.get('DB_PORT', 3307)) # puerto 3307 si se ejecuta en local; puerto 3306 para docker compose

        )
        if connection.is_connected():
            logger.info(f" Base MySQL consumida 🟢")
            return connection
    except Error as e:
        logger.critical(f" Error al conectar a base MySQL 🔴: {e}")
        return None