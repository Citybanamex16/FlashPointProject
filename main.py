from flask import Flask, jsonify
from flask_cors import CORS
from model import FlashPointModel

# 1. Creación de la app web
app = Flask(__name__)
CORS(app) 

# 2. Instanciación del Modelo
modelo = FlashPointModel(numAgents=0, width=10, height=8)

# 3. Definición de la Ruta / Endpoint
@app.route('/api/process', methods=['GET']) 
def GetSetupData():
    # Devuelve el DTO con el estado completo del tablero a Unity
    return jsonify(modelo.get_setup_dto()), 200

if __name__ == '__main__':
    # Ejecuta el servidor de Flask directamente en el hilo principal
    print("🚀 Servidor escuchando en http://127.0.0.1:5000/api/process")
    app.run(host='127.0.0.1', port=5000, debug=False)