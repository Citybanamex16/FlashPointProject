import random
from mesa import Model
from mesa.space import MultiGrid
from core_types import EstadoFuego, TipoPOI, POI, Nodo, Muro, Puerta
from agents import Rescuer, Role
import matplotlib.patches as patches
import matplotlib.pyplot as plt


class FlashPointModel(Model):
    def __init__(self, numAgents, width, height, verbose=True):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)
        self.bolsa_poi = []

        # --- Trackers globales y estado de la partida ---
        self.victimas_salvadas = 0
        self.victimas_perdidas = 0
        self.marcadores_dano = 24
        self.estado_juego = "EN_CURSO"
        self.reglas_familiares = True
        self.verbose = verbose

        self._fig = None
        self._ax = None

        self.mapa_nodos = {}
        for x in range(width):
            for y in range(height):
                nodo = Nodo(pos=(x, y))
                self.mapa_nodos[(x, y)] = nodo

        self._conectar_vecinos_base(width, height)
        self._cargar_infraestructura_tablero()
        self._preparar_juego_familiar()

        # 5. Instanciar y colocar agentes en las 4 puertas exteriores
        roles_disponibles = [
            Role.SEARCHER,
            Role.SOLDIER
        ]
        puertas_exteriores = [(3, 0), (6, 7), (0, 4), (9, 3)]

        for i in range(numAgents):
            rol_asignado = roles_disponibles[i % len(roles_disponibles)]
            bombero = Rescuer(self, role=rol_asignado)
            self.agents.add(bombero)

            # Asignar puerta exterior cíclicamente
            pos_inicial = puertas_exteriores[i % len(puertas_exteriores)]
            self.grid.place_agent(bombero, pos_inicial)
            self.mapa_nodos[pos_inicial].contenido.append(bombero)

    def _print(self, message):
        if self.verbose:
            print(message)

    def step(self):
        for agent in self.agents:
            agent.step()

            self._print("\n--- TURNO ---")
            # 1. Turnos de los agentes
            # 2. Fase de propagación del fuego
            self.avanzar_fuego()
            # 3. Resolver víctimas atrapadas y bomberos derribados
            self._resolver_knockdowns()
            # 4. Reponer POIs en el tablero
            self._reponer_pois()
            # 5. Evaluar condiciones de victoria/derrota
            self.evaluar_estado_juego()

            if self.estado_juego != "EN_CURSO":
                self._print(f"[FIN] {self.estado_juego}")
                return
            
            
    def evaluar_estado_juego(self):
        if self.victimas_salvadas >= 7:
            self.estado_juego = "VICTORIA"
            self.running = False
            self._print("[VICTORIA] 7 víctimas")

        elif self.victimas_perdidas >= 4:
            self.estado_juego = "DERROTA"
            self.running = False
            self._print("[DERROTA] 4 víctimas")

        elif self.marcadores_dano <= 0:
            self.estado_juego = "DERROTA"
            self.running = False
            self._print("[DERROTA] Edificio colapsó")

    def avanzar_fuego(self):
        target_x = random.randint(1, 8)
        target_y = random.randint(1, 6)
        nodo_objetivo = self.mapa_nodos[(target_x, target_y)]

        self._print(f"[DADOS] ({target_x}, {target_y})")

        if nodo_objetivo.estado_fuego == EstadoFuego.LIMPIO:
            nodo_objetivo.estado_fuego = EstadoFuego.HUMO
            self._print(f"[HUMO] ({target_x}, {target_y})")

        elif nodo_objetivo.estado_fuego == EstadoFuego.HUMO:
            nodo_objetivo.estado_fuego = EstadoFuego.FUEGO
            self._print(f"[FUEGO] ({target_x}, {target_y})")

        elif nodo_objetivo.estado_fuego == EstadoFuego.FUEGO:
            self._print(f"[EXPLOSION] ({target_x}, {target_y})")
            self._resolver_explosion(nodo_objetivo)

        self._resolver_flashovers()

    def _resolver_explosion(self, nodo_origen):
        x, y = nodo_origen.pos

        direcciones = [
            ((x + 1, y), "DERECHA", 1, 0),
            ((x - 1, y), "IZQUIERDA", -1, 0),
            ((x, y + 1), "ARRIBA", 0, 1),
            ((x, y - 1), "ABAJO", 0, -1)
        ]

        for pos_vecino, cardinal, dx, dy in direcciones:
            if pos_vecino not in self.mapa_nodos:
                continue

            nodo_vecino = self.mapa_nodos[pos_vecino]
            arista = nodo_origen.vecinos.get(nodo_vecino)

            if isinstance(arista, Muro) and arista.hp > 0:
                arista.golpear()
                self.marcadores_dano -= 1
                self._print(
                    f"[MURO] {nodo_origen.pos}->{pos_vecino} "
                    f"HP={arista.hp} D={self.marcadores_dano}"
                )
                continue

            if isinstance(arista, Puerta):
                if arista.cerrado:
                    arista.destruir()
                    self._print(f"[PUERTA] {pos_vecino} destruida")
                    continue
                else:
                    arista.destruir()
                    self._print(f"[PUERTA] {pos_vecino} destruida")

            if nodo_vecino.estado_fuego in [
                EstadoFuego.LIMPIO,
                EstadoFuego.HUMO
            ]:
                nodo_vecino.estado_fuego = EstadoFuego.FUEGO
                self._print(f"[IGNICION] {pos_vecino}")
                continue

            if nodo_vecino.estado_fuego == EstadoFuego.FUEGO:
                self._print(f"[ONDA] {pos_vecino}")
                self._proyectar_onda_choque(
                    nodo_vecino,
                    dx,
                    dy,
                    cardinal
                )

    def _proyectar_onda_choque(
        self,
        nodo_actual,
        dx,
        dy,
        cardinal
    ):
        paso = 1

        while True:
            siguiente_pos = (
                nodo_actual.pos[0] + dx,
                nodo_actual.pos[1] + dy
            )

            if siguiente_pos not in self.mapa_nodos:
                self._print("[ONDA] Sale del edificio")
                break

            nodo_siguiente = self.mapa_nodos[siguiente_pos]
            arista = nodo_actual.vecinos.get(nodo_siguiente)

            if isinstance(arista, Muro) and arista.hp > 0:
                arista.golpear()
                self.marcadores_dano -= 1

                self._print(
                    f"[MURO] {nodo_actual.pos}->{siguiente_pos} "
                    f"HP={arista.hp} D={self.marcadores_dano}"
                )
                break

            if isinstance(arista, Puerta):
                if arista.cerrado:
                    arista.destruir()
                    self._print(f"[PUERTA] {siguiente_pos} destruida")
                    break
                else:
                    arista.destruir()
                    self._print(f"[PUERTA] {siguiente_pos} destruida")

            if nodo_siguiente.estado_fuego in [
                EstadoFuego.LIMPIO,
                EstadoFuego.HUMO
            ]:
                nodo_siguiente.estado_fuego = EstadoFuego.FUEGO
                self._print(f"[IGNICION] {siguiente_pos}")
                break

            nodo_actual = nodo_siguiente
            paso += 1

    def _resolver_flashovers(self):
        iteracion = 1

        while True:
            cambios_en_ronda = 0

            for nodo in self.mapa_nodos.values():
                if nodo.estado_fuego == EstadoFuego.HUMO:
                    for vecino, arista in nodo.vecinos.items():
                        bloqueado = False

                        if isinstance(arista, Muro) and arista.hp > 0:
                            bloqueado = True

                        elif isinstance(arista, Puerta) and arista.cerrado:
                            bloqueado = True

                        if (
                            not bloqueado
                            and vecino.estado_fuego == EstadoFuego.FUEGO
                        ):
                            nodo.estado_fuego = EstadoFuego.FUEGO
                            cambios_en_ronda += 1
                            self._print(f"[FLASHOVER] {nodo.pos}")
                            break

            if cambios_en_ronda == 0:
                break

            iteracion += 1

    def _resolver_knockdowns(self):
        for nodo in self.mapa_nodos.values():
            if nodo.estado_fuego == EstadoFuego.FUEGO:
                # Iteramos al revés para poder remover elementos de la lista de forma segura
                for item in reversed(nodo.contenido):

                    if (
                        isinstance(item, POI)
                        and item.tipo == TipoPOI.VICTIMA
                    ):
                        nodo.contenido.remove(item)
                        self.victimas_perdidas += 1
                        self._print(
                            f"[BAJA] Víctima quemada en {nodo.pos} "
                            f"({self.victimas_perdidas}/4)"
                        )

                    elif type(item).__name__ == "Rescuer":
                        # 1. Calcular la ambulancia más cercana ("as the crow flies")
                        amb_1 = (0, 3)
                        amb_2 = (7, 7)
                        
                        # Usamos distancia euclidiana al cuadrado (a^2 + b^2 = c^2)
                        dist_1 = (nodo.pos[0] - amb_1[0])**2 + (nodo.pos[1] - amb_1[1])**2
                        dist_2 = (nodo.pos[0] - amb_2[0])**2 + (nodo.pos[1] - amb_2[1])**2
                        
                        ambulancia_destino = amb_1 if dist_1 <= dist_2 else amb_2

                        # 2. Remover del nodo en llamas y añadir a la ambulancia
                        nodo.contenido.remove(item)
                        self.mapa_nodos[ambulancia_destino].contenido.append(item)
                        
                        # 3. Sincronizar el motor de Mesa
                        self.grid.move_agent(item, ambulancia_destino)

                        self._print(f"[DERRIBO] Bombero en {nodo.pos} enviado a {ambulancia_destino}")

                        # 4. Manejar a la víctima en caso de que estuviese cargando una
                        if getattr(item, "llevando_victima", False):
                            item.llevando_victima = False
                            self.victimas_perdidas += 1
                            self._print(
                                f"[BAJA] Víctima cargada perdida en {nodo.pos} "
                                f"({self.victimas_perdidas}/4)"
                            )




    def _reponer_pois(self):
        pois_activos = sum(
            1
            for nodo in self.mapa_nodos.values()
            for item in nodo.contenido
            if isinstance(item, POI)
        )

        while pois_activos < 3 and self.bolsa_poi:
            target_x = random.randint(1, 8)
            target_y = random.randint(1, 6)
            nodo_objetivo = self.mapa_nodos[(target_x, target_y)]

            if any(
                isinstance(c, POI)
                for c in nodo_objetivo.contenido
            ):
                continue

            if nodo_objetivo.estado_fuego != EstadoFuego.LIMPIO:
                nodo_objetivo.estado_fuego = EstadoFuego.LIMPIO

            nuevo_poi = POI(self.bolsa_poi.pop())
            nodo_objetivo.contenido.append(nuevo_poi)
            pois_activos += 1

            self._print(f"[POI] ({target_x}, {target_y})")

            if any(
                type(c).__name__ == "Rescuer"
                for c in nodo_objetivo.contenido
            ):
                nuevo_poi.revelado = True
                self._print(
                    f"[POI] Revelado {nuevo_poi.tipo.name}"
                )

                if nuevo_poi.tipo == TipoPOI.FALSA_ALARMA:
                    nodo_objetivo.contenido.remove(nuevo_poi)
                    pois_activos -= 1
                    self._print("[POI] Falsa alarma")

    def _conectar_vecinos_base(self, width, height):
        for (x, y), nodo in self.mapa_nodos.items():
            direcciones = [
                (x + 1, y),
                (x - 1, y),
                (x, y + 1),
                (x, y - 1)
            ]

            for nx, ny in direcciones:
                if 0 <= nx < width and 0 <= ny < height:
                    nodo_vecino = self.mapa_nodos[(nx, ny)]
                    nodo.vecinos[nodo_vecino] = None

    def _colocar_borde(self, pos_a, pos_b, objeto_arista):
        nodo_a = self.mapa_nodos[pos_a]
        nodo_b = self.mapa_nodos[pos_b]

        nodo_a.vecinos[nodo_b] = objeto_arista
        nodo_b.vecinos[nodo_a] = objeto_arista

    def _cargar_infraestructura_tablero(self):
        lista_muros = [
            ((0, 1), (1, 1)),
            ((0, 2), (1, 2)),
            ((0, 3), (1, 3)),
            ((0, 5), (1, 5)),
            ((0, 6), (1, 6)),
            ((1, 0), (1, 1)),
            ((2, 0), (2, 1)),
            ((4, 0), (4, 1)),
            ((5, 0), (5, 1)),
            ((6, 0), (6, 1)),
            ((7, 0), (7, 1)),
            ((8, 0), (8, 1)),
            ((1, 6), (1, 7)),
            ((2, 6), (2, 7)),
            ((3, 6), (3, 7)),
            ((4, 6), (4, 7)),
            ((5, 6), (5, 7)),
            ((7, 6), (7, 7)),
            ((8, 6), (8, 7)),
            ((8, 1), (9, 1)),
            ((8, 2), (9, 2)),
            ((8, 4), (9, 4)),
            ((8, 5), (9, 5)),
            ((8, 6), (9, 6)),
            ((5, 2), (6, 2)),
            ((7, 2), (8, 2)),
            ((2, 3), (3, 3)),
            ((6, 4), (7, 4)),
            ((3, 5), (4, 5)),
            ((5, 6), (6, 6)),
            ((1, 2), (1, 3)),
            ((2, 2), (2, 3)),
            ((3, 2), (3, 3)),
            ((5, 2), (5, 3)),
            ((6, 2), (6, 3)),
            ((7, 2), (7, 3)),
            ((8, 2), (8, 3)),
            ((3, 4), (3, 5)),
            ((4, 4), (4, 5)),
            ((5, 4), (5, 5)),
            ((6, 4), (6, 5)),
            ((7, 4), (7, 5))
        ]

        lista_puertas = [
            ((3, 0), (3, 1)),
            ((0, 4), (1, 4)),
            ((6, 6), (6, 7)),
            ((8, 3), (9, 3)),
            ((7, 1), (8, 1)),
            ((5, 1), (6, 1)),
            ((4, 2), (4, 3)),
            ((6, 3), (7, 3)),
            ((2, 4), (3, 4)),
            ((8, 4), (8, 5)),
            ((3, 6), (4, 6)),
            ((5, 5), (6, 5))
        ]

        for pos_a, pos_b in lista_muros:
            if pos_a in self.mapa_nodos and pos_b in self.mapa_nodos:
                self._colocar_borde(pos_a, pos_b, Muro())

        for pos_a, pos_b in lista_puertas:
            if pos_a in self.mapa_nodos and pos_b in self.mapa_nodos:
                self._colocar_borde(pos_a, pos_b, Puerta())

    def _preparar_juego_familiar(self):
        fuegos_iniciales = [
            (6, 1),
            (6, 2),
            (7, 2),
            (4, 3),
            (2, 4),
            (3, 4),
            (4, 4),
            (5, 4),
            (2, 5),
            (3, 5)
        ]

        for pos in fuegos_iniciales:
            if pos in self.mapa_nodos:
                self.mapa_nodos[pos].estado_fuego = EstadoFuego.FUEGO

        self.bolsa_poi = (
            [TipoPOI.VICTIMA] * 10
            + [TipoPOI.FALSA_ALARMA] * 5
        )
        random.shuffle(self.bolsa_poi)

        pois_iniciales = [
            (1, 2),
            (8, 2),
            (4, 5)
        ]

        for pos in pois_iniciales:
            if pos in self.mapa_nodos:
                tipo_poi = self.bolsa_poi.pop()
                self.mapa_nodos[pos].contenido.append(POI(tipo_poi))

    def _exportar_nodos_dto(self):
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
        aristas_lista = []
        procesados = set()

        for nodo in self.mapa_nodos.values():
            pos_a = nodo.pos

            for nodo_vecino, arista in nodo.vecinos.items():
                if arista is not None and arista not in procesados:
                    procesados.add(arista)
                    pos_b = nodo_vecino.pos

                    arista_dto = {
                        "posA": {
                            "x": pos_a[0],
                            "y": pos_a[1]
                        },
                        "posB": {
                            "x": pos_b[0],
                            "y": pos_b[1]
                        },
                        "tipo": arista.tipo.name
                    }

                    if isinstance(arista, Puerta):
                        arista_dto["cerrado"] = arista.cerrado

                    elif isinstance(arista, Muro):
                        arista_dto["hp"] = arista.hp

                    aristas_lista.append(arista_dto)

        return aristas_lista

    def get_setup_dto(self):
        return {
            "width": self.grid.width,
            "height": self.grid.height,
            "nodes": self._exportar_nodos_dto(),
            "edges": self._exportar_aristas_dto()
        }

    def visualizar_matplot(self, figsize=(10, 8)):
        if self._fig is None or not plt.fignum_exists(self._fig.number):
            self._fig, self._ax = plt.subplots(figsize=figsize)
        else:
            self._ax.clear()

        color_fuego = {
            EstadoFuego.LIMPIO: "#E0E0E0",
            EstadoFuego.HUMO: "#808080",
            EstadoFuego.FUEGO: "#FF4500"
        }

        # DIBUJAR CELDAS Y CONTENIDOS
        for (x, y), nodo in self.mapa_nodos.items():
            color = color_fuego.get(
                nodo.estado_fuego,
                "#FFFFFF"
            )

            rect = patches.Rectangle(
                (x, y),
                1,
                1,
                facecolor=color,
                edgecolor="#D3D3D3",
                lw=0.5
            )

            self._ax.add_patch(rect)

            # EXTRAER BOMBEROS DIRECTAMENTE DE LA GRID DE MESA
            bomberos = [
                c
                for c in self.grid.get_cell_list_contents((x, y))
                if type(c).__name__ == "Rescuer"
            ]

            # Dibujar Bomberos
            if bomberos:
                circle = patches.Circle(
                    (x + 0.5, y + 0.5),
                    0.35,
                    facecolor="#1E90FF",
                    edgecolor="black",
                    lw=1.5,
                    zorder=3
                )

                self._ax.add_patch(circle)

                # Indicador de víctima cargada
                if any(
                    getattr(b, "llevando_victima", False)
                    for b in bomberos
                ):
                    self._ax.text(
                        x + 0.5,
                        y + 0.5,
                        "V",
                        ha="center",
                        va="center",
                        fontsize=10,
                        fontweight="bold",
                        color="#FFFF00",
                        zorder=5
                    )

            # Dibujar POIs
            elif any(
                isinstance(c, POI)
                for c in nodo.contenido
            ):
                self._ax.text(
                    x + 0.5,
                    y + 0.5,
                    "?",
                    ha="center",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                    color="black",
                    zorder=4
                )

        # DIBUJAR MUROS Y PUERTAS
        procesados = set()

        for (x, y), nodo in self.mapa_nodos.items():
            for vecino, arista in nodo.vecinos.items():
                if arista is None or arista in procesados:
                    continue

                procesados.add(arista)
                nx, ny = vecino.pos

                if nx == x + 1:
                    line_x, line_y = [x + 1, x + 1], [y, y + 1]

                elif nx == x - 1:
                    line_x, line_y = [x, x], [y, y + 1]

                elif ny == y + 1:
                    line_x, line_y = [x, x + 1], [y + 1, y + 1]

                else:
                    line_x, line_y = [x, x + 1], [y, y]

                if isinstance(arista, Muro):
                    if arista.hp == 2:
                        self._ax.plot(
                            line_x,
                            line_y,
                            color="black",
                            lw=4,
                            solid_capstyle="round"
                        )

                    elif arista.hp == 1:
                        self._ax.plot(
                            line_x,
                            line_y,
                            color="#8B4513",
                            lw=2.5,
                            linestyle="--"
                        )

                elif isinstance(arista, Puerta):
                    color_p = (
                        "#0000FF"
                        if arista.cerrado
                        else "#32CD32"
                    )

                    self._ax.plot(
                        line_x,
                        line_y,
                        color=color_p,
                        lw=3,
                        linestyle=":"
                    )

        self._ax.set_xlim(0, self.grid.width)
        self._ax.set_ylim(0, self.grid.height)
        self._ax.set_xticks(range(self.grid.width + 1))
        self._ax.set_yticks(range(self.grid.height + 1))
        self._ax.set_aspect("equal")
        self._ax.grid(False)

        self._ax.set_title(
            f"Flash Point | Daño: {self.marcadores_dano}/24 | "
            f"Víctimas: {self.victimas_salvadas} Salvadas, "
            f"{self.victimas_perdidas} Perdidas | "
            f"Estado: {self.estado_juego}"
        )

        plt.draw()
        plt.pause(0.01)