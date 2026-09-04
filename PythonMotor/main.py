from model import FlashPointModel

if __name__ == "__main__":
    # Test initialization
    modelo = FlashPointModel(numAgents=0, width=10, height=8)
    modelo.imprimir_tablero_debug()