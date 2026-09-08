import random
from mesa import Model
from mesa.space import MultiGrid
from core_types import EstadoFuego, TipoPOI, POI, Nodo, Muro, Puerta
import matplotlib.patches as patches
import matplotlib.pyplot as plt

class FlashPointModel(Model):
    def __init__(self, numAgents, width, height):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)
        self.bolsa_poi = []

        # --- Trackers globales y estado de la partida ---
        self.victimas_salvadas = 0     
        self.victimas_perdidas = 0     
        self.marcadores_dano = 24      
        self.estado_juego = "EN_CURSO"
        self.reglas_familiares = True  

        # Referencias persistentes para renderizado interactivo sin duplicar ventanas
        self._fig = None
        self._ax = None

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
            print(f"\n[PARTIDA FINALIZADA]: {self.estado_juego}")
            return

        print("\n" + "=" * 50)
        print(">>> INICIO DE TURNO (FASE DE ENTORNO / HAZARDS) <<<")
        print("=" * 50)

        # 1. Turnos de los agentes (Pendiente hasta integrar agents.py)
        # self.schedule.step()

        # 2. Fase de propagación del fuego
        self.avanzar_fuego()

        # 3. Resolver víctimas atrapadas y bomberos derribados
        self._resolver_knockdowns()

        # 4. Reponer POIs en el tablero
        self._reponer_pois()

        # 5. Evaluar condiciones de victoria/derrota
        self.evaluar_estado_juego()

    def evaluar_estado_juego(self):
        if self.victimas_salvadas >= 7:
            self.estado_juego = "VICTORIA"
            self.running = False
            print("\n[RESULTADO GLOBAL]: ¡VICTORIA! Se rescataron 7 víctimas.")
        elif self.victimas_perdidas >= 4:
            self.estado_juego = "DERROTA"
            self.running = False
            print("\n[RESULTADO GLOBAL]: ¡DERROTA! Murieron 4 víctimas.")
        elif self.marcadores_dano <= 0:
            self.estado_juego = "DERROTA"
            self.running = False
            print("\n[RESULTADO GLOBAL]: ¡DERROTA! El edificio colapsó (0 marcadores de daño).")

    def avanzar_fuego(self):
        target_x = random.randint(1, 8)
        target_y = random.randint(1, 6)
        nodo_objetivo = self.mapa_nodos[(target_x, target_y)]

        print(f"\n[DADOS]: Tirada ({target_x}, {target_y})")

        if nodo_objetivo.estado_fuego == EstadoFuego.LIMPIO:
            nodo_objetivo.estado_fuego = EstadoFuego.HUMO
            print(f"  └─ Estado anterior: LIMPIO -> Colocado HUMO en ({target_x}, {target_y})")
        elif nodo_objetivo.estado_fuego == EstadoFuego.HUMO:
            nodo_objetivo.estado_fuego = EstadoFuego.FUEGO
            print(f"  └─ Estado anterior: HUMO -> Combustión a FUEGO en ({target_x}, {target_y})")
        elif nodo_objetivo.estado_fuego == EstadoFuego.FUEGO:
            print(f"  └─ Estado anterior: FUEGO -> ¡💥 EXPLOSIÓN INICIADA en ({target_x}, {target_y})!")
            self._resolver_explosion(nodo_objetivo)

        self._resolver_flashovers()

    def _resolver_explosion(self, nodo_origen):
        x, y = nodo_origen.pos
        direcciones = [((x+1, y), "DERECHA", 1, 0),
                       ((x-1, y), "IZQUIERDA", -1, 0),
                       ((x, y+1), "ARRIBA", 0, 1),
                       ((x, y-1), "ABAJO", 0, -1)]

        for pos_vecino, cardinal, dx, dy in direcciones:
            if pos_vecino not in self.mapa_nodos:
                continue

            nodo_vecino = self.mapa_nodos[pos_vecino]
            arista = nodo_origen.vecinos.get(nodo_vecino)

            print(f"    [RAMA EXPLOSIÓN {cardinal}]: Verificando arista/celda hacia {pos_vecino}...")

            # 1. Colisión con muro
            if isinstance(arista, Muro) and arista.hp > 0:
                arista.golpear()
                self.marcadores_dano -= 1
                print(f"      ├─ IMPACTO EN MURO: Muro entre {nodo_origen.pos} y {pos_vecino} pierde 1 HP (HP actual: {arista.hp}).")
                print(f"      └─ Marcadores de daño restantes: {self.marcadores_dano}/24")
                continue

            # 2. Colisión con puerta
            if isinstance(arista, Puerta):
                if arista.cerrado:
                    arista.destruir()
                    print(f"      └─ IMPACTO EN PUERTA: Puerta cerrada en {pos_vecino} DESTRUIDA. La explosión se frena.")
                    continue
                else:
                    arista.destruir()
                    print(f"      ├─ Puerta abierta en {pos_vecino} destruida por el paso del fuego.")

            # 3. Ignición de espacio adyacente
            if nodo_vecino.estado_fuego in [EstadoFuego.LIMPIO, EstadoFuego.HUMO]:
                nodo_vecino.estado_fuego = EstadoFuego.FUEGO
                print(f"      └─ IGNICIÓN: Celda {pos_vecino} convertida a FUEGO. La onda se disipa.")
                continue

            # 4. Celda adyacente en fuego: proyectar onda de choque
            if nodo_vecino.estado_fuego == EstadoFuego.FUEGO:
                print(f"      ├─ Fuego existente en {pos_vecino}. Propagando onda de choque...")
                self._proyectar_onda_choque(nodo_vecino, dx, dy, cardinal)

    def _proyectar_onda_choque(self, nodo_actual, dx, dy, cardinal):
        paso = 1
        while True:
            siguiente_pos = (nodo_actual.pos[0] + dx, nodo_actual.pos[1] + dy)
            if siguiente_pos not in self.mapa_nodos:
                print(f"        └─ [ONDA {cardinal}]: La onda sale del edificio en {siguiente_pos}. Fin de trayectoria.")
                break

            nodo_siguiente = self.mapa_nodos[siguiente_pos]
            arista = nodo_actual.vecinos.get(nodo_siguiente)

            # Colisión con muro
            if isinstance(arista, Muro) and arista.hp > 0:
                arista.golpear()
                self.marcadores_dano -= 1
                print(f"        └─ [ONDA {cardinal} - Paso {paso}]: Muro golpeado entre {nodo_actual.pos} y {siguiente_pos} (HP: {arista.hp}).")
                print(f"           Marcadores de daño restantes: {self.marcadores_dano}/24")
                break

            # Colisión con puerta
            if isinstance(arista, Puerta):
                if arista.cerrado:
                    arista.destruir()
                    print(f"        └─ [ONDA {cardinal} - Paso {paso}]: Puerta cerrada destruida en {siguiente_pos}. Fin de onda.")
                    break
                else:
                    arista.destruir()
                    print(f"        ├─ [ONDA {cardinal} - Paso {paso}]: Puerta abierta destruida al pasar.")

            # Ignición
            if nodo_siguiente.estado_fuego in [EstadoFuego.LIMPIO, EstadoFuego.HUMO]:
                nodo_siguiente.estado_fuego = EstadoFuego.FUEGO
                print(f"        └─ [ONDA {cardinal} - Paso {paso}]: Espacio libre ignita a FUEGO en {siguiente_pos}. Fin de trayectoria.")
                break

            print(f"        ├─ [ONDA {cardinal} - Paso {paso}]: Traspasa fuego en {siguiente_pos} sin detenerse.")
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

                        if not bloqueado and vecino.estado_fuego == EstadoFuego.FUEGO:
                            nodo.estado_fuego = EstadoFuego.FUEGO
                            cambios_en_ronda += 1
                            print(f"  [FLASHOVER Ciclo {iteracion}]: Humo en {nodo.pos} se inflama a FUEGO (contacto con {vecino.pos}).")
                            break

            if cambios_en_ronda == 0:
                break
            iteracion += 1

    def _resolver_knockdowns(self):
        for nodo in self.mapa_nodos.values():
            if nodo.estado_fuego == EstadoFuego.FUEGO:
                for item in reversed(nodo.contenido):
                    if isinstance(item, POI) and item.tipo == TipoPOI.VICTIMA:
                        nodo.contenido.remove(item)
                        self.victimas_perdidas += 1
                        print(f"  [BAJA]: 💀 Víctima consumida por el fuego en {nodo.pos}. Total perdidas: {self.victimas_perdidas}/4")
                    elif type(item).__name__ == "Firefighter":
                        nodo.contenido.remove(item)
                        self.mapa_nodos[(0, 0)].contenido.append(item)
                        item.pos = (0, 0)
                        print(f"  [DERRIBO]: 🚑 Bombero alcanzado por las llamas en {nodo.pos}. Teletransportado a (0, 0).")
                        if getattr(item, 'llevando_victima', False):
                            item.llevando_victima = False
                            self.victimas_perdidas += 1
                            print(f"  [BAJA]: 💀 La víctima que cargaba perece en el incidente. Total perdidas: {self.victimas_perdidas}/4")

    def _reponer_pois(self):
        pois_activos = sum(
            1 for nodo in self.mapa_nodos.values()
            for item in nodo.contenido if isinstance(item, POI)
        )

        while pois_activos < 3 and self.bolsa_poi:
            target_x = random.randint(1, 8)
            target_y = random.randint(1, 6)
            nodo_objetivo = self.mapa_nodos[(target_x, target_y)]

            if any(isinstance(c, POI) for c in nodo_objetivo.contenido):
                print(f"  [REPOSICIÓN POI]: Coordenada ({target_x}, {target_y}) ya tiene un POI. Reintentando...")
                continue

            if nodo_objetivo.estado_fuego != EstadoFuego.LIMPIO:
                print(f"  [REPOSICIÓN POI]: Limpiando {nodo_objetivo.estado_fuego.name} en ({target_x}, {target_y}) según reglas familiares.")
                nodo_objetivo.estado_fuego = EstadoFuego.LIMPIO

            nuevo_poi = POI(self.bolsa_poi.pop())
            nodo_objetivo.contenido.append(nuevo_poi)
            pois_activos += 1
            print(f"  [REPOSICIÓN POI]: 📍 Colocado nuevo POI oculto en ({target_x}, {target_y}). POIs en mesa: {pois_activos}/3. Restantes en bolsa: {len(self.bolsa_poi)}")

            if any(type(c).__name__ == "Firefighter" for c in nodo_objetivo.contenido):
                nuevo_poi.revelado = True
                print(f"  [REPOSICIÓN POI]: Revelado inmediato en ({target_x}, {target_y}) por presencia de bombero -> Tipo: {nuevo_poi.tipo.name}")
                if nuevo_poi.tipo == TipoPOI.FALSA_ALARMA:
                    nodo_objetivo.contenido.remove(nuevo_poi)
                    pois_activos -= 1
                    print("  [REPOSICIÓN POI]: Falsa alarma descartada al instante.")

    def _conectar_vecinos_base(self, width, height):
        for (x, y), nodo in self.mapa_nodos.items():
            direcciones = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
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
        fuegos_iniciales = [(6,1), (6,2), (7,2), (4,3),(2,4),(3,4),(4,4),(5,4),(2,5),(3,5)]
        for pos in fuegos_iniciales:
            if pos in self.mapa_nodos:
                self.mapa_nodos[pos].estado_fuego = EstadoFuego.FUEGO

        self.bolsa_poi = [TipoPOI.VICTIMA] * 10 + [TipoPOI.FALSA_ALARMA] * 5
        random.shuffle(self.bolsa_poi)

        pois_iniciales = [(1,2), (8,2), (4,5)]
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
            EstadoFuego.FUEGO: "#FF4500",
        }

        for (x, y), nodo in self.mapa_nodos.items():
            color = color_fuego.get(nodo.estado_fuego, "#FFFFFF")
            rect = patches.Rectangle((x, y), 1, 1, facecolor=color, edgecolor="#D3D3D3", lw=0.5)
            self._ax.add_patch(rect)

            if any(isinstance(c, POI) for c in nodo.contenido):
                self._ax.text(x + 0.5, y + 0.5, "?", ha="center", va="center", fontsize=14, fontweight="bold", color="black")

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
                        self._ax.plot(line_x, line_y, color="black", lw=4, solid_capstyle="round")
                    elif arista.hp == 1:
                        self._ax.plot(line_x, line_y, color="#8B4513", lw=2.5, linestyle="--")
                elif isinstance(arista, Puerta):
                    color_p = "#0000FF" if arista.cerrado else "#32CD32"
                    self._ax.plot(line_x, line_y, color=color_p, lw=3, linestyle=":")

        self._ax.set_xlim(0, self.grid.width)
        self._ax.set_ylim(0, self.grid.height)
        self._ax.set_xticks(range(self.grid.width + 1))
        self._ax.set_yticks(range(self.grid.height + 1))
        self._ax.set_aspect("equal")
        self._ax.grid(False)
        self._ax.set_title(f"Flash Point | Daño: {self.marcadores_dano}/24 | Víctimas: {self.victimas_salvadas} Salvadas, {self.victimas_perdidas} Perdidas | Estado: {self.estado_juego}")
        
        plt.draw()
        plt.pause(0.01)