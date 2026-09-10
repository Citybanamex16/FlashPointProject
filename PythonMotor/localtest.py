import matplotlib.pyplot as plt
from model import FlashPointModel

# Activar modo interactivo de matplotlib
plt.ion()

print("Inicializando FlashPointModel (10x8 - Reglas Familiares)...")
modelo = FlashPointModel(numAgents=6, width=10, height=8)

# Renderizar estado inicial
modelo.visualizar_matplot()

print("\n" + "=" * 55)
print("CONTROL DE PRUEBA LOCAL (TERMINAL)")
print(" Comandos:")
print("   's' -> Ejecutar step() (Avanzar fuego, knockdowns, POIs)")
print("   'q' -> Salir del programa")
print("=" * 55)

while True:
    try:
        comando = input("\n[FlashPoint] Ingrese comando ('s'/'q'): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        break

    if comando == 's':
        if modelo.estado_juego != "EN_CURSO":
            print(f"El juego ha terminado con estado: {modelo.estado_juego}. Saliendo...")
            break

        modelo.step()
        modelo.visualizar_matplot()

    elif comando == 'q':
        print("Saliendo de la prueba interactiva.")
        break
    else:
        print("Comando no reconocido. Use 's' para step o 'q' para salir.")

plt.ioff()
plt.close('all')