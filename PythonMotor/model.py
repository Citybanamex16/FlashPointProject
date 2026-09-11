import random
from mesa import Model
from mesa.space import MultiGrid
from core_types import EstadoFuego, TipoPOI, POI, Nodo, Muro, Puerta
from agents import AgentAction, AgentStatus, RandomRescuer, Rescuer, Role
import matplotlib.patches as patches
import matplotlib.pyplot as plt


class FlashPointModel(Model):
    def __init__(self, numAgents, width, height, verbose=False):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)
        self.bolsa_poi = []

        # --- sets de objetos afectados durante step
        self.nodos_afectados = set()  # Almacena (x, y) como llave 
        self.aristas_afectadas = set() # Almacena (posA, posB) como llave 
        self.agentes_afectados = set()

        # --- Tracker de POIs ---
        self.pois_reclamados = {}  
        self.fuegos_reclamados = {}
        self.pois_perdidos = []

        # --- Trackers globales y estado de la partida ---
        self.victimas_salvadas = 0
        self.victimas_perdidas = 0
        self.falsas_alarmas_resueltas = 0
        self.marcadores_dano = 24
        self.estado_juego = "EN_CURSO"
        self.ultima_tirada = None
        self.reglas_familiares = True
        self.verbose = verbose

        self._fig = None
        self._ax = None
        self.visualizar_acciones_turno = False
        self.pausa_visualizacion = 0.5
        self._texto_visualizacion = ""

        self.mapa_nodos = {} # Llave: ((x1, y1), (x2, y2)) -> Valor: Objeto Nodo
        self.mapa_aristas = {} # Llave: ((x1, y1), (x2, y2)) -> Valor: Objeto Arista


        for x in range(width):
            for y in range(height):
                nodo = Nodo(pos=(x, y))
                self.mapa_nodos[(x, y)] = nodo

        self._conectar_vecinos_base(width, height)
        # Crear mapa de 
        self._cargar_infraestructura_tablero()
        self._preparar_juego_familiar()

        roles_disponibles = [
            Role.SEARCHER,
            Role.SOLDIER,
            Role.SOLDIER,
            Role.SOLDIER,
            Role.SOLDIER,
            Role.SOLDIER
        ]
        puertas_exteriores = [(3, 0), (6, 7), (0, 4), (9, 3)]

        for i in range(numAgents):
            rol_asignado = roles_disponibles[i % len(roles_disponibles)]
            bombero = Rescuer(self, role=rol_asignado)
            self.agents.add(bombero)

            pos_inicial = puertas_exteriores[i % len(puertas_exteriores)]
            self.grid.place_agent(bombero, pos_inicial)
            self.mapa_nodos[pos_inicial].contenido.append(bombero)

    def _asignar_busqueda_inicial(self):
        # Detecta los POIs ya colocados en el tablero al iniciar la partida
        # (los de _preparar_juego_familiar) y asigna, a cada uno, al agente
        # con menor costo de ruta hasta esa celda. Ese agente pasa a
        # SEARCHER y queda bloqueado (role_bloqueado) hasta completar un
        # rescate de ida y vuelta o encontrar una falsa alarma.
        posiciones_poi = [
            pos
            for pos, nodo in self.mapa_nodos.items()
            if any(isinstance(c, POI) for c in nodo.contenido)
        ]

        agentes_disponibles = sorted(
            self.agents, key=lambda agente: agente.unique_id
        )

        for poi_pos in posiciones_poi:
            if not agentes_disponibles:
                break

            mejor_agente = None
            mejor_costo = float('inf')

            for agente in agentes_disponibles:
                _, costo = agente._encontrar_ruta_optima([poi_pos])
                if costo < mejor_costo:
                    mejor_costo = costo
                    mejor_agente = agente

            if mejor_agente is not None:
                mejor_agente.role = Role.SEARCHER
                mejor_agente.role_bloqueado = True
                mejor_agente._poi_objetivo = poi_pos
                self.pois_reclamados[poi_pos] = mejor_agente
                agentes_disponibles.remove(mejor_agente)
                self._print(
                    f"[SETUP] Agente {mejor_agente.unique_id} asignado como "
                    f"searcher dedicado a POI {poi_pos}"
                )

    def _print(self, message):
        if self.verbose:
            print(message)


    # === Funciones de Marcado de Nodos/Aristas en Step ===
    def _marcar_nodo(self, nodo):
        self.nodos_afectados.add(nodo.pos)

    def _marcar_arista(self, arista):
        if hasattr(arista, 'key'):
            self.aristas_afectadas.add(arista.key)

    def _marcar_agente(self, agente):
        self.agentes_afectados.add(agente.unique_id)

    def _visualizar_accion_agente(self, agente):
        if not self.visualizar_acciones_turno:
            return

        self._texto_visualizacion = (
            f"Agente {agente.unique_id} | {agente.role.name} | "
            f"Accion: {agente.accion_actual.value} | AP: {agente.ap}"
        )
        self.visualizar_matplot()
        plt.pause(self.pausa_visualizacion)

    def _recalcular_roles_dinamicos(self):
        # Release POI claims from agents that are no longer acting.
        for pos, agente in list(self.pois_reclamados.items()):
            if agente.estado == AgentStatus.KNOCKED_DOWN:
                del self.pois_reclamados[pos]
                # Red de seguridad: si un searcher dedicado es derribado a
                # mitad de su misión, no debe quedar bloqueado para siempre.
                if agente.role_bloqueado:
                    agente.role_bloqueado = False

        agentes = sorted(self.agents, key=lambda agente: agente.unique_id)
        total_agentes = len(agentes)
        fuegos_activos = sum(
            1
            for nodo in self.mapa_nodos.values()
            if nodo.estado_fuego == EstadoFuego.FUEGO
        )

        min_searchers = 1
        max_searchers = max(min_searchers, round(total_agentes * 0.5))

        if fuegos_activos <= 3:
            objetivo_searchers = max_searchers
        elif fuegos_activos >= 8:
            objetivo_searchers = min_searchers
        else:
            return

        # Los searchers dedicados (role_bloqueado) cuentan para el total,
        # pero nunca pueden ser elegidos como candidatos para (des)promover:
        # deben completar su misión de ida y vuelta primero.
        searchers_actuales = [
            agente for agente in agentes if agente.role == Role.SEARCHER
        ]
        soldiers_actuales = [
            agente for agente in agentes if agente.role == Role.SOLDIER
        ]
        diferencia = objetivo_searchers - len(searchers_actuales)

        if diferencia > 0:
            candidatos = sorted(
                (a for a in soldiers_actuales if not a.role_bloqueado),
                key=lambda agente: (agente.llevando_victima, agente.unique_id)
            )
            for agente in candidatos[:diferencia]:
                agente.role = Role.SEARCHER

        elif diferencia < 0:
            candidatos = sorted(
                (a for a in searchers_actuales if not a.role_bloqueado),
                key=lambda agente: (agente.llevando_victima, agente.unique_id)
            )
            for agente in candidatos[:abs(diferencia)]:
                agente.role = Role.SOLDIER
                agente._poi_objetivo = None
                agente._fuego_objetivo = None
                for pos, owner in list(self.pois_reclamados.items()):
                    if owner == agente:
                        del self.pois_reclamados[pos]

    def step(self):

        # -- Limpiamos los conjuntos al iniciar el step --- #
        # -- SUPER MACRO IMPORTANTE -- #

        self.nodos_afectados.clear()
        self.aristas_afectadas.clear()
        self.agentes_afectados.clear()

        self._recalcular_roles_dinamicos()

        for agent in sorted(self.agents, key=lambda agente: agente.unique_id):
            agent.step()
            self.evaluar_estado_juego()
            if self.estado_juego != "EN_CURSO":
                return

            self._print("\n--- TURNO ---")
            # 1. Turnos de los agentes
            # 2. Fase de propagación del fuego
            self.avanzar_fuego()
            if self.estado_juego != "EN_CURSO":
                return
            # 3. Resolver víctimas atrapadas y bomberos derribados
            self._resolver_knockdowns()
            if self.estado_juego != "EN_CURSO":
                return
            self._limpiar_fuego_exterior()
            # 4. Reponer POIs en el tablero
            self._reponer_pois()
            # 5. Evaluar condiciones de victoria/derrota
            self.evaluar_estado_juego()

            if self.estado_juego != "EN_CURSO":
                self._print(f"[FIN] {self.estado_juego}")
                return
                
            
    def evaluar_estado_juego(self):
        if self.estado_juego != "EN_CURSO":
            return
        if self.victimas_salvadas >= 7:
            self.estado_juego = "VICTORIA"
            self.running = False
            self._print("[VICTORIA] 7 víctimas")

        elif self.victimas_perdidas >= 4:
            self.estado_juego = "DERROTA"
            self.running = False
            self._print("[DERROTA] 4 víctimas")

        elif self.marcadores_dano <= 0:
            self._finalizar_colapso()

    def _danar_muro(self, muro):
        muro.golpear()
        self.marcadores_dano = max(0, self.marcadores_dano - 1)
        self._marcar_arista(muro)
        if self.marcadores_dano == 0:
            self._finalizar_colapso()
            return False
        return True

    def _finalizar_colapso(self):
        if self.estado_juego != "EN_CURSO":
            return
        self.estado_juego = "DERROTA"
        self.running = False
        for nodo in self.mapa_nodos.values():
            for item in list(nodo.contenido):
                if isinstance(item, POI):
                    nodo.contenido.remove(item)
                    self.pois_perdidos.append(item)
                    if item.tipo == TipoPOI.VICTIMA:
                        self.victimas_perdidas += 1
                    self._marcar_nodo(nodo)
        for agente in sorted(self.agents, key=lambda agente: agente.unique_id):
            if agente.llevando_victima:
                agente.llevando_victima = False
                self.victimas_perdidas += 1
                self._marcar_agente(agente)
        self.pois_reclamados.clear()
        self.fuegos_reclamados.clear()
        self._print("[DERROTA] Edificio colapsó")


    def avanzar_fuego(self):
        target_x = random.randint(1, 8)
        target_y = random.randint(1, 6)
        self.ultima_tirada = (target_x, target_y)
        nodo_objetivo = self.mapa_nodos[(target_x, target_y)]

        self._print(f"[DADOS] ({target_x}, {target_y})")

        if nodo_objetivo.estado_fuego == EstadoFuego.LIMPIO:
            nodo_objetivo.estado_fuego = EstadoFuego.HUMO
            self._print(f"[HUMO] ({target_x}, {target_y})")
            self._marcar_nodo(nodo_objetivo)

        elif nodo_objetivo.estado_fuego == EstadoFuego.HUMO:
            nodo_objetivo.estado_fuego = EstadoFuego.FUEGO
            self._print(f"[FUEGO] ({target_x}, {target_y})")
            self._marcar_nodo(nodo_objetivo)

        elif nodo_objetivo.estado_fuego == EstadoFuego.FUEGO:
            self._print(f"[EXPLOSION] ({target_x}, {target_y})")
            self._resolver_explosion(nodo_objetivo)

        if self.estado_juego != "EN_CURSO":
            return
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
                if not self._danar_muro(arista):
                    return
                self._print(
                    f"[MURO] {nodo_origen.pos}->{pos_vecino} "
                    f"HP={arista.hp} D={self.marcadores_dano}"
                )
                continue

            if isinstance(arista, Puerta):
                if arista.cerrado:
                    arista.destruir()
                    self._print(f"[PUERTA] {pos_vecino} destruida")
                    self._marcar_arista(arista)
                    continue
                else:
                    arista.destruir()
                    self._print(f"[PUERTA] {pos_vecino} destruida")
                    self._marcar_arista(arista)

            if nodo_vecino.estado_fuego in [
                EstadoFuego.LIMPIO,
                EstadoFuego.HUMO
            ]:
                nodo_vecino.estado_fuego = EstadoFuego.FUEGO
                self._marcar_nodo(nodo_vecino)
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
                if self.estado_juego != "EN_CURSO":
                    return

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
                if not self._danar_muro(arista):
                    return
                self._print(
                    f"[MURO] {nodo_actual.pos}->{siguiente_pos} "
                    f"HP={arista.hp} D={self.marcadores_dano}"
                )
                break

            if isinstance(arista, Puerta):
                if arista.cerrado:
                    arista.destruir()
                    self._marcar_arista(arista)
                    self._print(f"[PUERTA] {siguiente_pos} destruida")
                    break
                else:
                    arista.destruir()
                    self._marcar_arista(arista)
                    self._print(f"[PUERTA] {siguiente_pos} destruida")

            if nodo_siguiente.estado_fuego in [
                EstadoFuego.LIMPIO,
                EstadoFuego.HUMO
            ]:
                nodo_siguiente.estado_fuego = EstadoFuego.FUEGO
                self._marcar_nodo(nodo_siguiente)
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
                            self._marcar_nodo(nodo)
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

                    if isinstance(item, POI):
                        item.revelado = True
                        nodo.contenido.remove(item)
                        self.pois_perdidos.append(item)
                        self._marcar_nodo(nodo)
                        if item.tipo == TipoPOI.VICTIMA:
                            self.victimas_perdidas += 1
                            self._print(
                                f"[BAJA] Víctima quemada en {nodo.pos} "
                                f"({self.victimas_perdidas}/4)"
                            )
                            self.evaluar_estado_juego()
                            if self.estado_juego != "EN_CURSO":
                                return
                        else:
                            self._print(
                                f"[BAJA] Falsa alarma quemada en {nodo.pos}"
                            )

                    elif isinstance(item, RandomRescuer):
                        if item.estado == AgentStatus.KNOCKED_DOWN:
                            continue
                        # 1. Calcular la ambulancia más cercana ("as the crow flies")
                        amb_1 = (0, 3)
                        amb_2 = (7, 7)
                        
                        # Usamos distancia euclidiana al cuadrado (a^2 + b^2 = c^2)
                        dist_1 = (nodo.pos[0] - amb_1[0])**2 + (nodo.pos[1] - amb_1[1])**2
                        dist_2 = (nodo.pos[0] - amb_2[0])**2 + (nodo.pos[1] - amb_2[1])**2
                        
                        ambulancia_destino = amb_1 if dist_1 <= dist_2 else amb_2

                        nodo_amb = self.mapa_nodos[ambulancia_destino]

                        # 2. Remover del nodo en llamas y añadir a la ambulancia
                        nodo.contenido.remove(item)
                        nodo_amb.contenido.append(item)
                        
                        # 3. Sincronizar el motor de Mesa
                        self.grid.move_agent(item, ambulancia_destino)

                        item.estado = AgentStatus.KNOCKED_DOWN
                        item.registrar_accion(
                            AgentAction.KNOCKED_DOWN,
                            ambulancia_destino
                        )
                        
                        self._marcar_nodo(nodo_amb)
                        self._marcar_nodo(nodo)

                        self._print(f"[DERRIBO] Bombero en {nodo.pos} enviado a {ambulancia_destino}")

                        # 4. Manejar a la víctima en caso de que estuviese cargando una
                        if getattr(item, "llevando_victima", False):
                            item.knocked_down_carrying_victim += 1
                            item.llevando_victima = False
                            self.victimas_perdidas += 1
                            self._marcar_nodo(nodo)
                            self._print(
                                f"[BAJA] Víctima cargada perdida en {nodo.pos} "
                                f"({self.victimas_perdidas}/4)"
                            )
                            self.evaluar_estado_juego()
                            if self.estado_juego != "EN_CURSO":
                                return

    def _limpiar_fuego_exterior(self):
        ancho = self.grid.width - 1
        alto = self.grid.height - 1
        for (x, y), nodo in self.mapa_nodos.items():
            if (
                nodo.estado_fuego == EstadoFuego.FUEGO
                and (x == 0 or x == ancho or y == 0 or y == alto)
            ):
                nodo.estado_fuego = EstadoFuego.LIMPIO
                self._marcar_nodo(nodo)




    def _reponer_pois(self):
        pois_activos = sum(
            1
            for nodo in self.mapa_nodos.values()
            for item in nodo.contenido
            if isinstance(item, POI)
        ) + sum(agente.llevando_victima for agente in self.agents)

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
                self._print(
                    f"[POI] Sobrescribe {nodo_objetivo.estado_fuego.name} "
                    f"en ({target_x},{target_y})"
                )
                nodo_objetivo.estado_fuego = EstadoFuego.LIMPIO

            nuevo_poi = POI(self.bolsa_poi.pop())
            nodo_objetivo.contenido.append(nuevo_poi)
            pois_activos += 1

            self._print(f"[POI] ({target_x}, {target_y})")

            if any(
                isinstance(c, RandomRescuer)
                for c in nodo_objetivo.contenido
            ):
                nuevo_poi.revelado = True
                self._print(
                    f"[POI] Revelado {nuevo_poi.tipo.name}"
                )

                if nuevo_poi.tipo == TipoPOI.FALSA_ALARMA:
                    nodo_objetivo.contenido.remove(nuevo_poi)
                    self.falsas_alarmas_resueltas += 1
                    pois_activos -= 1
                    self._print("[POI] Falsa alarma")

            self._marcar_nodo(nodo_objetivo)

    def _celda_adyacente_a_fuego(self, nodo):
        for vecino, arista in nodo.vecinos.items():
            if isinstance(arista, Muro) and arista.hp > 0:
                continue
            if isinstance(arista, Puerta) and arista.cerrado:
                continue
            if vecino.estado_fuego == EstadoFuego.FUEGO:
                return True
        return False



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

        # === MODELO SE ENTERA DE LA RELACION ===
        key = (pos_a, pos_b)
        objeto_arista.key = key # Inyectamos la clave al objeto
        self.mapa_aristas[key] = objeto_arista

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
                        arista_dto["destruida"] = arista.destruida

                    elif isinstance(arista, Muro):
                        arista_dto["hp"] = arista.hp

                    aristas_lista.append(arista_dto)

        return aristas_lista

    def get_setup_dto(self):
        return {
            "width": self.grid.width,
            "height": self.grid.height,
            "nodes": self._exportar_nodos_dto(),
            "edges": self._exportar_aristas_dto(),
            "agents": [
                self._agente_a_dto(agent)
                for agent in sorted(self.agents, key=lambda agente: agente.unique_id)
            ],
            "poi_tracker": self._poi_tracker_dto()
        }


# ===Recoleccion de datos de Agente=== #


    def posicion_a_dto(self,posicion):
        if posicion is None:
            return None
        return {"x": posicion[0], "y": posicion[1]}

    def _agente_a_dto(self, agente):
        return {
            "id": agente.unique_id,
            "rol": agente.role.name,
            "posicion": self.posicion_a_dto(agente.pos),
            "posicion_anterior": self.posicion_a_dto(agente.posicion_anterior),
            "posicion_objetivo": self.posicion_a_dto(agente.posicion_objetivo),
            "accion": agente.accion_actual.value,
            "acciones_turno": [accion.value for accion in agente.acciones_turno],
            "eventos_turno": agente.eventos_turno,
            "ap": agente.ap,
            "ap_guardados": agente.saved_ap,
            "llevando_victima": agente.llevando_victima,
            "estado": agente.estado.name
        }


# === Funciones Auxiliares para Step DTO === #
    
    def _nodo_a_dto(self, nodo):
        poi_dto = None
        for item in nodo.contenido:
            if isinstance(item, POI):
                poi_dto = {
                    "tipo": item.tipo.name,
                    "revelado": item.revelado
                }
                break

        return {
            "x": nodo.pos[0],
            "y": nodo.pos[1],
            "fuego": nodo.estado_fuego.name,
            "poi": poi_dto
        }


    def _arista_a_dto(self, key):
        arista = self.mapa_aristas[key]
        pos_a, pos_b = key

        dto = {
            "posA": {"x": pos_a[0], "y": pos_a[1]},
            "posB": {"x": pos_b[0], "y": pos_b[1]},
            "tipo": arista.tipo.name
        }

        if isinstance(arista, Puerta):
            dto["cerrado"] = arista.cerrado
            dto["destruida"] = arista.destruida
        elif isinstance(arista, Muro):
            dto["hp"] = arista.hp

        return dto

    def get_step_dto(self, target_x=None, target_y=None):
        tirada = self.ultima_tirada
        if target_x is not None and target_y is not None:
            tirada = (target_x, target_y)
        return {
                "estado_juego": self.estado_juego,
                "marcadores_dano": self.marcadores_dano,
                "victimas_salvadas": self.victimas_salvadas,
                "victimas_perdidas": self.victimas_perdidas,
                "tirada_dados": (
                    None if tirada is None else {"x": tirada[0], "y": tirada[1]}
                ),
                "poi_tracker": self._poi_tracker_dto(),

                # Solo enviamos la transformación a DTO de los elementos que cambiaron
                "nodes": [self._nodo_a_dto(self.mapa_nodos[pos]) for pos in self.nodos_afectados],
                "edges": [self._arista_a_dto(key) for key in self.aristas_afectadas],
                "agents": [
                    self._agente_a_dto(agent)
                    for agent in sorted(
                        self.agents, key=lambda agente: agente.unique_id
                    )
                    if agent.unique_id in self.agentes_afectados
                ]
            }

    def _poi_tracker_dto(self):
        tablero_victimas = 0
        tablero_falsas = 0
        for nodo in self.mapa_nodos.values():
            for item in nodo.contenido:
                if isinstance(item, POI):
                    if item.tipo == TipoPOI.VICTIMA:
                        tablero_victimas += 1
                    else:
                        tablero_falsas += 1
        transportadas = sum(agente.llevando_victima for agente in self.agents)
        perdidas_falsas = sum(
            item.tipo == TipoPOI.FALSA_ALARMA for item in self.pois_perdidos
        )
        bolsa_victimas = self.bolsa_poi.count(TipoPOI.VICTIMA)
        bolsa_falsas = self.bolsa_poi.count(TipoPOI.FALSA_ALARMA)
        return {
            "victimas": {
                "bolsa": bolsa_victimas,
                "tablero": tablero_victimas,
                "transportadas": transportadas,
                "salvadas": self.victimas_salvadas,
                "perdidas": self.victimas_perdidas,
            },
            "falsas_alarmas": {
                "bolsa": bolsa_falsas,
                "tablero": tablero_falsas,
                "resueltas": self.falsas_alarmas_resueltas,
                "perdidas": perdidas_falsas,
            },
            "activos": tablero_victimas + tablero_falsas + transportadas,
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
                if isinstance(c, RandomRescuer)
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
            + (f" | {self._texto_visualizacion}" if self._texto_visualizacion else "")
        )

        plt.draw()
        plt.pause(0.01)
