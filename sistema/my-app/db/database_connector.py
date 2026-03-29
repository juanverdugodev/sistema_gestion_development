import mysql.connector
import logging
from mysql.connector import Error
import os

logger = logging.getLogger(__name__)

def get_db_connection(target_db=None):
    """
    Crea una conexión a la base de datos MySQL.
    Si target_db no se define, se conecta a la base de datos principal por defecto.
    """
    # Determinar qué base de datos usar
    db_to_use = target_db if target_db else os.environ.get('DB_NAME', 'sistema_gestion_db')

    try:
        connection = mysql.connector.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            user=os.environ.get('DB_USER', 'app_user'),
            password=os.environ.get('DB_PASSWORD', 'App@p4ssw0rd26'),
            database=db_to_use,
            port=int(os.environ.get('DB_PORT', 3306))
        )
        if connection.is_connected():
            logger.info(f"Base MySQL conectada 🟢 ({db_to_use})")
            return connection
            
    except Error as e:
        logger.critical(f"Error al conectar a base MySQL 🔴 ({db_to_use}): {e}")
        return None