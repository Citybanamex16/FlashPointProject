import random
from mesa import Model
from mesa.space import MultiGrid
from core_types import EstadoFuego, TipoPOI, POI, Nodo, Muro, Puerta
import matplotlib.patches as patches
import matplotlib.pyplot as plt

class FlashPointModel(Model):
    def __init__(self, numAgents, width, height):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)  # grid de vectores 2D
        self.bolsa_poi = []

        # --- Trackers globales y estado de la partida ---
        self.victimas_salvadas = 0     # 7 para ganar
        self.victimas_perdidas = 0     # 4 para perder
        self.marcadores_dano = 24      # 0 para perder por colapso del edificio
        self.estado_juego = "EN_CURSO" # "EN_CURSO", "VICTORIA", "DERROTA"
        self.reglas_familiares = True  # bloquea vehículos y mecánicas avanzadas

        # 1. Crear matriz de nodos
        self.mapa_nodos = {}
        for x in range(width):
            for y in range(height):
                nodo = Nodo(pos=(x, y))
                self.mapa_nodos[(x, y)] = nodo

        # 2. Conectar cada nodo con sus vecinos ortogonales
        self._conectar_vecinos_base(width, height)

        # 3. Colocar muros y puertas del tablero
        self._cargar_infraestructura_tablero()

        # 4. Preparar el setup de la partida familiar
        self._preparar_juego_familiar()

    def step(self):
        if self.estado_juego != "EN_CURSO":
            return

        # 1. Turnos de los agentes (pendiente hasta implementar el schedule)
        # self.schedule.step()

        # 2. Fase de fuego
        self.avanzar_fuego()

        # 3. Resolver víctimas atrapadas y bomberos derribados
        self._resolver_knockdowns()

        # 4. Reponer POIs en el tablero
        self._reponer_pois()

        # 5. Evaluar condiciones de victoria/derrota
        self.evaluar_estado_juego()

    def _resolver_knockdowns(self):
        # Revisa cada espacio en llamas y resuelve víctimas y bomberos atrapados ahí
        for nodo in self.mapa_nodos.values():
            if nodo.estado_fuego == EstadoFuego.FUEGO:
                # Iteramos en reversa para poder remover elementos mientras recorremos
                for item in reversed(nodo.contenido):
                    # Víctima atrapada en el fuego: se pierde
                    if isinstance(item, POI) and item.tipo == TipoPOI.VICTIMA:
                        nodo.contenido.remove(item)
                        self.victimas_perdidas += 1

                    # Bombero derribado: se teletransporta a la ambulancia
                    elif type(item).__name__ == "Firefighter":
                        nodo.contenido.remove(item)
                        self.mapa_nodos[(0, 0)].contenido.append(item)
                        item.pos = (0, 0)

                        # Si llevaba una víctima, esta muere al instante
                        if getattr(item, 'llevando_victima', False):
                            item.llevando_victima = False
                            self.victimas_perdidas += 1

    def _reponer_pois(self):
        # Cuenta los POIs activos (sin revelar o víctimas reveladas) en el tablero
        pois_activos = sum(
            1 for nodo in self.mapa_nodos.values()
            for item in nodo.contenido if isinstance(item, POI)
        )

        # Repone hasta llegar exactamente a 3 POIs activos
        while pois_activos < 3 and self.bolsa_poi:
            target_x = random.randint(1, 8)
            target_y = random.randint(1, 6)
            nodo_objetivo = self.mapa_nodos[(target_x, target_y)]

            # Si ya hay un POI en ese espacio, se vuelve a tirar
            if any(isinstance(c, POI) for c in nodo_objetivo.contenido):
                continue

            # Reglas familiares: se limpia cualquier fuego/humo antes de colocar el POI
            if nodo_objetivo.estado_fuego != EstadoFuego.LIMPIO:
                nodo_objetivo.estado_fuego = EstadoFuego.LIMPIO

            # Se saca el siguiente POI de la bolsa (ya mezclada) y se coloca
            nuevo_poi = POI(self.bolsa_poi.pop())
            nodo_objetivo.contenido.append(nuevo_poi)
            pois_activos += 1

            # Revelación instantánea si el POI cae sobre un bombero
            if any(type(c).__name__ == "Firefighter" for c in nodo_objetivo.contenido):
                nuevo_poi.revelado = True
                if nuevo_poi.tipo == TipoPOI.FALSA_ALARMA:
                    nodo_objetivo.contenido.remove(nuevo_poi)
                    pois_activos -= 1  # obliga a repetir el ciclo y sacar otro

    def evaluar_estado_juego(self):
        # Condición de victoria
        if self.victimas_salvadas >= 7:
            self.estado_juego = "VICTORIA"
            self.running = False

        # Condiciones de derrota
        elif self.victimas_perdidas >= 4:
            self.estado_juego = "DERROTA"
            self.running = False

        elif self.marcadores_dano <= 0:
            self.estado_juego = "DERROTA"
            self.running = False

    def avanzar_fuego(self):
        # 1. Tirada de dados: negro de 8 caras (eje X) y rojo de 6 caras (eje Y)
        target_x = random.randint(1, 8)
        target_y = random.randint(1, 6)
        nodo_objetivo = self.mapa_nodos[(target_x, target_y)]

        # 2. Lógica de ignición según el estado actual del espacio
        if nodo_objetivo.estado_fuego == EstadoFuego.LIMPIO:
            nodo_objetivo.estado_fuego = EstadoFuego.HUMO

        elif nodo_objetivo.estado_fuego == EstadoFuego.HUMO:
            nodo_objetivo.estado_fuego = EstadoFuego.FUEGO

        elif nodo_objetivo.estado_fuego == EstadoFuego.FUEGO:
            self._resolver_explosion(nodo_objetivo)

        # 3. Resolver flashovers después de la ignición
        self._resolver_flashovers()

    def _proyectar_onda_choque(self, nodo_actual, dx, dy):
        # Propaga la onda de choque de una explosión en línea recta
        while True:
            siguiente_pos = (nodo_actual.pos[0] + dx, nodo_actual.pos[1] + dy)

            # Se detiene si la onda sale del tablero
            if siguiente_pos not in self.mapa_nodos:
                break

            nodo_siguiente = self.mapa_nodos[siguiente_pos]
            arista = nodo_actual.vecinos.get(nodo_siguiente)

            # 1. Colisión con muro o puerta
            if isinstance(arista, Muro) and arista.hp > 0:
                arista.golpear()
                self.marcadores_dano -= 1
                break  # la onda es absorbida por el muro

            if isinstance(arista, Puerta):
                if arista.cerrado:
                    arista.destruir()
                    break  # la onda es absorbida por la puerta cerrada
                else:
                    arista.destruir()

            # 2. Ignición por la onda
            if nodo_siguiente.estado_fuego in [EstadoFuego.LIMPIO, EstadoFuego.HUMO]:
                nodo_siguiente.estado_fuego = EstadoFuego.FUEGO
                break  # se detiene tras encender un espacio limpio o con humo

            # Si el espacio ya está en fuego, la onda sigue en la misma dirección
            nodo_actual = nodo_siguiente

    def _resolver_explosion(self, nodo_origen):
        x, y = nodo_origen.pos

        # Evalúa las cuatro direcciones ortogonales desde el origen
        for nodo_vecino, arista in nodo_origen.vecinos.items():
            dx = nodo_vecino.pos[0] - x
            dy = nodo_vecino.pos[1] - y

            # 1. Colisión inmediata con muro o puerta
            if isinstance(arista, Muro) and arista.hp > 0:
                arista.golpear()
                self.marcadores_dano -= 1
                continue  # la explosión se detiene tras dañar el muro

            if isinstance(arista, Puerta):
                if arista.cerrado:
                    arista.destruir()
                    continue  # se detiene tras destruir la puerta cerrada
                else:
                    arista.destruir()  # pasa por la puerta abierta pero la destruye

            # 2. Ignición del espacio vecino
            if nodo_vecino.estado_fuego in [EstadoFuego.LIMPIO, EstadoFuego.HUMO]:
                nodo_vecino.estado_fuego = EstadoFuego.FUEGO
                continue  # se detiene tras encender el espacio

            # 3. Si el vecino ya está en fuego, se dispara la onda de choque
            if nodo_vecino.estado_fuego == EstadoFuego.FUEGO:
                self._proyectar_onda_choque(nodo_vecino, dx, dy)

    def _resolver_flashovers(self):
        # Repite el barrido hasta que ningún humo quede junto a fuego
        flashover_ocurrido = True

        while flashover_ocurrido:
            flashover_ocurrido = False

            for nodo in self.mapa_nodos.values():
                if nodo.estado_fuego == EstadoFuego.HUMO:
                    for vecino, arista in nodo.vecinos.items():
                        # Un muro o puerta cerrada bloquea el flashover
                        bloqueado = False
                        if isinstance(arista, Muro) and arista.hp > 0:
                            bloqueado = True
                        elif isinstance(arista, Puerta) and arista.cerrado:
                            bloqueado = True

                        if not bloqueado and vecino.estado_fuego == EstadoFuego.FUEGO:
                            nodo.estado_fuego = EstadoFuego.FUEGO
                            flashover_ocurrido = True
                            break  # nodo actualizado, se pasa al siguiente

    def _conectar_vecinos_base(self, width, height):
        # Conecta cada nodo con sus vecinos arriba/abajo/izquierda/derecha
        for (x, y), nodo in self.mapa_nodos.items():
            direcciones = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
            for nx, ny in direcciones:
                if 0 <= nx < width and 0 <= ny < height:
                    nodo_vecino = self.mapa_nodos[(nx, ny)]
                    nodo.vecinos[nodo_vecino] = None

    def _colocar_borde(self, pos_a, pos_b, objeto_arista):
        # Coloca un muro o puerta entre dos nodos (relación bidireccional)
        nodo_a = self.mapa_nodos[pos_a]
        nodo_b = self.mapa_nodos[pos_b]
        nodo_a.vecinos[nodo_b] = objeto_arista
        nodo_b.vecinos[nodo_a] = objeto_arista

    def _cargar_infraestructura_tablero(self):
        lista_muros = [
            ((0,1), (1,1)), ((0,2), (1,2)), ((0,3), (1,3)), ((0,5), (1,5)), ((0,6), (1,6)),
            ((1,0), (1,1)), ((2,0), (2,1)),
            ((4,0), (4,1)), ((5,0), (5,1)), ((6,0), (6,1)), ((7,0), (7,1)), ((8,0), (8,1)),
            ((1,6), (1,7)), ((2,6), (2,7)), ((3,6), (3,7)), ((4,6), (4,7)), ((5,6), (5,7)), ((7,6), (7,7)), ((8,6), (8,7)),
            ((8,1), (9,1)), ((8,2), (9,2)), ((8,4), (9,4)), ((8,5), (9,5)), ((8,6), (9,6)),
            ((5,2), (6,2)), ((7,2), (8,2)), ((2,3), (3,3)), ((6,4), (7,4)), ((3,5), (4,5)), ((5,6), (6,6)),
            ((1,2), (1,3)), ((2,2), (2,3)), ((3,2), (3,3)), ((5,2), (5,3)), ((6,2), (6,3)), ((7,2), (7,3)), ((8,2), (8,3)),
            ((3,4), (3,5)), ((4,4), (4,5)), ((5,4), (5,5)), ((6,4), (6,5)), ((7,4), (7,5))
        ]

        lista_puertas = [
            ((3,0), (3,1)), ((0,4), (1,4)), ((6,6), (6,7)), ((8,3), (9,3)),
            ((7,1), (8,1)), ((5,1), (6,1)), ((4,2), (4,3)), ((6,3), (7,3)),
            ((2,4), (3,4)), ((8,4), (8,5)), ((3,6), (4,6)), ((5,5), (6,5))
        ]

        for pos_a, pos_b in lista_muros:
            if pos_a in self.mapa_nodos and pos_b in self.mapa_nodos:
                self._colocar_borde(pos_a, pos_b, Muro())

        for pos_a, pos_b in lista_puertas:
             if pos_a in self.mapa_nodos and pos_b in self.mapa_nodos:
                self._colocar_borde(pos_a, pos_b, Puerta())

    def _preparar_juego_familiar(self):
        # Fuegos iniciales del setup familiar
        fuegos_iniciales = [(6,1), (6,2), (7,2), (4,3),(2,4),(3,4),(4,4),(5,4),(2,5),(3,5)]
        for pos in fuegos_iniciales:
            if pos in self.mapa_nodos:
                self.mapa_nodos[pos].estado_fuego = EstadoFuego.FUEGO

        # Bolsa de POIs: 10 víctimas y 5 falsas alarmas, mezcladas
        self.bolsa_poi = [TipoPOI.VICTIMA] * 10 + [TipoPOI.FALSA_ALARMA] * 5
        random.shuffle(self.bolsa_poi)

        # POIs iniciales en sus posiciones fijas
        pois_iniciales = [(1,2), (8,2), (4,5)]
        for pos in pois_iniciales:
            if pos in self.mapa_nodos:
                tipo_poi = self.bolsa_poi.pop()
                self.mapa_nodos[pos].contenido.append(POI(tipo_poi))

    # ==== Sistema de DTO Python -> Unity ==== #
    def _exportar_nodos_dto(self):
        # Serializa cada nodo (posición, estado de fuego y POI si tiene) a dict
        nodos_lista = []
        for nodo in self.mapa_nodos.values():
            x, y = nodo.pos

            poi_dto = None
            for item in nodo.contenido:
                if isinstance(item, POI):
                    poi_dto = {
                        "tipo": item.tipo.name,
                        "revelado": item.revelado
                    }
                    break

            nodo_dto = {
                "x": x,
                "y": y,
                "fuego": nodo.estado_fuego.name,
                "poi": poi_dto
            }
            nodos_lista.append(nodo_dto)

        return nodos_lista

    def _exportar_aristas_dto(self):
        # Serializa muros y puertas evitando duplicados (cada arista es compartida por 2 nodos)
        aristas_lista = []
        procesados = set()

        for nodo in self.mapa_nodos.values():
            pos_a = nodo.pos

            for nodo_vecino, arista in nodo.vecinos.items():
                if arista is not None and arista not in procesados:
                    procesados.add(arista)
                    pos_b = nodo_vecino.pos

                    arista_dto = {
                        "posA": {"x": pos_a[0], "y": pos_a[1]},
                        "posB": {"x": pos_b[0], "y": pos_b[1]},
                        "tipo": arista.tipo.name
                    }

                    if isinstance(arista, Puerta):
                        arista_dto["cerrado"] = arista.cerrado
                    elif isinstance(arista, Muro):
                        arista_dto["hp"] = arista.hp

                    aristas_lista.append(arista_dto)

        return aristas_lista

    def get_setup_dto(self):
        # Punto de entrada para exportar el estado inicial del tablero a Unity
        return {
            "width": self.grid.width,
            "height": self.grid.height,
            "nodes": self._exportar_nodos_dto(),
            "edges": self._exportar_aristas_dto()
        }

    ## === Visualización DEBUG === ##
    def imprimir_tablero_debug(self):
        # Dibuja el tablero como texto en consola para depuración rápida
        print("\n" + "=" * 48)
        print("             DEBUG: MAPA DE FLASH POINT")
        print("    [ ]=Limpio [H]=Humo [F]=Fuego | ? = POI Oculto")
        print("    ║/═ Muro (2HP) | │/─ Muro (1HP) | D/d Puerta")
        print("=" * 48 + "\n")

        for y in range(self.grid.height - 1, -1, -1):
            linea_horizontal = "  "
            for x in range(self.grid.width):
                nodo_actual = self.mapa_nodos[(x, y)]
                nodo_arriba = self.mapa_nodos.get((x, y + 1))
                if nodo_arriba and nodo_arriba in nodo_actual.vecinos:
                    borde = nodo_actual.vecinos[nodo_arriba]
                    linea_horizontal += self._simbolo_borde_horizontal(borde)
                else:
                    linea_horizontal += "─────"
            print(linea_horizontal)

            linea_nodos = f"{y} "
            for x in range(self.grid.width):
                nodo_actual = self.mapa_nodos[(x, y)]
                nodo_derecha = self.mapa_nodos.get((x + 1, y))

                simbolo_fuego = " "
                if nodo_actual.estado_fuego == EstadoFuego.FUEGO: simbolo_fuego = "F"
                elif nodo_actual.estado_fuego == EstadoFuego.HUMO: simbolo_fuego = "H"

                simbolo_poi = "?" if any(isinstance(c, POI) for c in nodo_actual.contenido) else " "
                linea_nodos += f"[{simbolo_fuego}{simbolo_poi}]"

                if nodo_derecha and nodo_derecha in nodo_actual.vecinos:
                    borde = nodo_actual.vecinos[nodo_derecha]
                    linea_nodos += self._simbolo_borde_vertical(borde)
                else:
                    linea_nodos += " "
            print(linea_nodos)

        print("  " + "─────" * self.grid.width)
        eje_x = "  " + "".join(f"  {x}  " for x in range(self.grid.width))
        print(eje_x + "\n")

    def _simbolo_borde_horizontal(self, borde):
        if borde is None: return "     "
        if isinstance(borde, Muro):
            if borde.hp == 2: return "════ "
            elif borde.hp == 1: return "──── "
            return "     "
        if isinstance(borde, Puerta):
            return "  D  " if borde.cerrado else "  d  "
        return "     "

    def _simbolo_borde_vertical(self, borde):
        if borde is None: return " "
        if isinstance(borde, Muro):
            if borde.hp == 2: return "║"
            elif borde.hp == 1: return "│"
            return " "
        if isinstance(borde, Puerta):
            return "D" if borde.cerrado else "d"
        return " "

    # otra visualización debug, pero más clara (con matplotlib)
    def visualizar_matplot(self, figsize=(10, 8)):
        fig, ax = plt.subplots(figsize=figsize)

        color_fuego = {
            EstadoFuego.LIMPIO: "#E0E0E0",  # gris claro (limpio)
            EstadoFuego.HUMO: "#808080",    # gris oscuro
            EstadoFuego.FUEGO: "#FF4500",   # rojo anaranjado
        }

        # 1. Fondo de cada celda y su hazard
        for (x, y), nodo in self.mapa_nodos.items():
            color = color_fuego.get(nodo.estado_fuego, "#FFFFFF")
            rect = patches.Rectangle(
                (x, y), 1, 1, facecolor=color, edgecolor="#D3D3D3", lw=0.5
            )
            ax.add_patch(rect)

            # marcador de POI
            if any(isinstance(c, POI) for c in nodo.contenido):
                ax.text(
                    x + 0.5,
                    y + 0.5,
                    "?",
                    ha="center",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                    color="black",
                )

        # 2. Muros y puertas en los bordes de las celdas
        procesados = set()
        for (x, y), nodo in self.mapa_nodos.items():
            for vecino, arista in nodo.vecinos.items():
                if arista is None or arista in procesados:
                    continue
                procesados.add(arista)

                nx, ny = vecino.pos

                # coordenadas del segmento según la dirección del vecino
                if nx == x + 1:  # derecha
                    line_x, line_y = [x + 1, x + 1], [y, y + 1]
                elif nx == x - 1:  # izquierda
                    line_x, line_y = [x, x], [y, y + 1]
                elif ny == y + 1:  # arriba
                    line_x, line_y = [x, x + 1], [y + 1, y + 1]
                else:  # abajo
                    line_x, line_y = [x, x + 1], [y, y]

                # estilo según tipo y estado de la arista
                if isinstance(arista, Muro):
                    if arista.hp == 2:
                        ax.plot(
                            line_x,
                            line_y,
                            color="black",
                            lw=4,
                            solid_capstyle="round",
                        )
                    elif arista.hp == 1:
                        ax.plot(
                            line_x,
                            line_y,
                            color="#8B4513",
                            lw=2.5,
                            linestyle="--",
                        )
                elif isinstance(arista, Puerta):
                    color_p = "#0000FF" if arista.cerrado else "#32CD32"
                    ax.plot(line_x, line_y, color=color_p, lw=3, linestyle=":")

        # 3. Ajustes de vista y ejes
        ax.set_xlim(0, self.grid.width)
        ax.set_ylim(0, self.grid.height)
        ax.set_xticks(range(self.grid.width + 1))
        ax.set_yticks(range(self.grid.height + 1))
        ax.set_aspect("equal")
        ax.grid(False)
        plt.title("Flash Point: Fire Rescue - Tablero")
        plt.show()