from flask import Flask, jsonify
from flask_cors import CORS
from model import FlashPointModel

app = Flask(__name__)
CORS(app) 

@app.route('/api/init', methods=['GET']) 
def GetSetupData():
    global modelo
    modelo = FlashPointModel(numAgents=6, width=10, height=8)
    return jsonify(modelo.get_setup_dto()), 200

@app.route('/api/step', methods=['GET'])
def GetStepData():
    modelo.step()
    return jsonify(modelo.get_step_dto()), 200


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
