from flask import Flask, jsonify
from flask_cors import CORS
from model import FlashPointModel



# 1. Creación de la app web
app = Flask(__name__)
CORS(app) 


# 2. Ruta de inicialiazacion
@app.route('/api/init', methods=['GET']) 
def GetSetupData():
    global modelo
    modelo = FlashPointModel(numAgents=4, width=10, height=8)
    return jsonify(modelo.get_setup_dto()), 200

# 3. Ruta de Step
@app.route('/api/step', methods=['GET'])
def GetStepData():
    modelo.step()
    return jsonify(modelo.get_step_dto()), 200


if __name__ == '__main__':
    #print("📊 Visualización inicial del modelo:")
    #modelo.visualizar_matplot()


    # Ejecuta el servidor de Flask directamente en el hilo principal
    print("🚀 Servidor escuchando en http://127.0.0.1:5000/api/process")
    app.run(host='127.0.0.1', port=5000, debug=False)

