# Importamos la app desde app.py
from app import create_app

app = create_app ()
if __name__ == "__main__":
    # debug=True permite que la app se recargue auto para desarrollo
    app.run(debug=True)