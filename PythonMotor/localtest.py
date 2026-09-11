import random

from model import FlashPointModel

random.seed(20260910)
modelo = FlashPointModel(numAgents=6, width=10, height=8)

while True:
    try:
        comando = input().strip().lower()
    except (KeyboardInterrupt, EOFError):
        break

    if comando == 's':
        if modelo.estado_juego != "EN_CURSO":
            break

        modelo.step()
    elif comando == "q":
        break
