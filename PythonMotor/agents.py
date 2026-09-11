import heapq
import random
from enum import Enum

from mesa import Agent

from core_types import EstadoFuego, Muro, POI, Puerta, TipoPOI


class Role(Enum):
    SEARCHER = "Searcher"
    WALLBREAKER = "Wallbreaker"
    SOLDIER = "Soldier"


class AgentAction(Enum):
    IDLE = "IDLE"
    MOVE = "MOVE"
    OPEN_DOOR = "OPEN_DOOR"
    CLOSE_DOOR = "CLOSE_DOOR"
    BREAK_WALL = "BREAK_WALL"
    EXTINGUISH = "EXTINGUISH"
    SEARCH = "SEARCH"
    PICK_UP_VICTIM = "PICK_UP_VICTIM"
    RESCUE_VICTIM = "RESCUE_VICTIM"
    DROP_VICTIM = "DROP_VICTIM"
    KNOCKED_DOWN = "KNOCKED_DOWN"


class AgentStatus(Enum):
    ACTIVE = "ACTIVE"
    KNOCKED_DOWN = "KNOCKED_DOWN"


class RandomRescuer(Agent):
    def __init__(self, model, role=Role.SEARCHER):
        super().__init__(model)
        self.role = role
        self.ap = 4
        self.saved_ap = 0
        self.llevando_victima = False
        self.accion_actual = AgentAction.IDLE
        self.posicion_anterior = None
        self.posicion_objetivo = None
        self._poi_objetivo = None
        self._fuego_objetivo = None
        self.acciones_turno = []
        self.eventos_turno = []
        self.estado = AgentStatus.ACTIVE
        self.role_bloqueado = False
        self.turns_without_progress = 0
        self._last_target_distance = None
        self.ap_gastado_moviendo = 0
        self.ap_gastado_actuando = 0
        self.knocked_down_carrying_victim = 0

    def registrar_accion(self, accion, objetivo=None):
        self.accion_actual = accion
        self.posicion_objetivo = objetivo
        self.acciones_turno.append(accion)
        self.eventos_turno.append({
            "accion": accion.value,
            "posicion": {"x": self.pos[0], "y": self.pos[1]},
            "posicion_objetivo": (
                None
                if objetivo is None
                else {"x": objetivo[0], "y": objetivo[1]}
            ),
            "ap": self.ap,
            "llevando_victima": self.llevando_victima,
            "estado": self.estado.name,
        })
        self.model._marcar_agente(self)
        self.model._visualizar_accion_agente(self)

    def step(self):
        if self.estado == AgentStatus.KNOCKED_DOWN:
            self.estado = AgentStatus.ACTIVE

        self._iniciar_turno()
        self._interactuar_celda_actual()

        while self.ap > 0:
            acciones = self._acciones_legales()
            if not acciones:
                break

            tipo, objetivo = random.choice(acciones)
            if tipo == AgentAction.MOVE:
                self._mover(objetivo)
            elif tipo == AgentAction.OPEN_DOOR:
                self._abrir_puerta(objetivo)
            elif tipo == AgentAction.EXTINGUISH:
                self._extinguir(objetivo)

        self._terminar_turno()

    def _iniciar_turno(self):
        self.posicion_anterior = self.pos
        self.posicion_objetivo = None
        self._poi_objetivo = None
        self._fuego_objetivo = None
        self.accion_actual = AgentAction.IDLE
        self.acciones_turno = []
        self.eventos_turno = []
        self.ap = min(8, self.saved_ap + 4)
        self.saved_ap = 0

    def _terminar_turno(self):
        self.saved_ap = min(4, self.ap)
        self.ap = 0

    def _acciones_legales(self):
        acciones = []
        nodo_actual = self.model.mapa_nodos[self.pos]

        if nodo_actual.estado_fuego == EstadoFuego.HUMO and self.ap >= 1:
            acciones.append((AgentAction.EXTINGUISH, self.pos))
        elif nodo_actual.estado_fuego == EstadoFuego.FUEGO and self.ap >= 2:
            acciones.append((AgentAction.EXTINGUISH, self.pos))

        for vecino, arista in nodo_actual.vecinos.items():
            if isinstance(arista, Puerta) and arista.cerrado:
                if not arista.destruida and self.ap >= 1:
                    acciones.append((AgentAction.OPEN_DOOR, vecino.pos))
                continue
            if isinstance(arista, Muro) and arista.hp > 0:
                continue

            if vecino.estado_fuego == EstadoFuego.HUMO and self.ap >= 1:
                acciones.append((AgentAction.EXTINGUISH, vecino.pos))
            elif vecino.estado_fuego == EstadoFuego.FUEGO and self.ap >= 2:
                acciones.append((AgentAction.EXTINGUISH, vecino.pos))

            costo_movimiento = 2 if (
                self.llevando_victima
                or vecino.estado_fuego == EstadoFuego.FUEGO
            ) else 1
            if (
                self.ap >= costo_movimiento
                and not (
                    self.llevando_victima
                    and vecino.estado_fuego == EstadoFuego.FUEGO
                )
            ):
                acciones.append((AgentAction.MOVE, vecino.pos))

        return acciones

    def _mover(self, objetivo):
        nodo_origen = self.model.mapa_nodos[self.pos]
        nodo_destino = self.model.mapa_nodos[objetivo]
        costo = 2 if (
            self.llevando_victima
            or nodo_destino.estado_fuego == EstadoFuego.FUEGO
        ) else 1

        self.ap -= costo
        self.ap_gastado_moviendo += costo
        nodo_origen.contenido.remove(self)
        self.model.grid.move_agent(self, objetivo)
        nodo_destino.contenido.append(self)
        self.model._marcar_nodo(nodo_origen)
        self.model._marcar_nodo(nodo_destino)
        self.registrar_accion(AgentAction.MOVE, objetivo)
        self._interactuar_celda_actual()

    def _abrir_puerta(self, objetivo):
        nodo_actual = self.model.mapa_nodos[self.pos]
        nodo_destino = self.model.mapa_nodos[objetivo]
        puerta = nodo_actual.vecinos[nodo_destino]

        self.ap -= 1
        self.ap_gastado_actuando += 1
        puerta.abrir()
        self.model._marcar_arista(puerta)
        self.registrar_accion(AgentAction.OPEN_DOOR, objetivo)

    def _extinguir(self, objetivo):
        nodo = self.model.mapa_nodos[objetivo]
        costo = 1 if nodo.estado_fuego == EstadoFuego.HUMO else 2

        self.ap -= costo
        self.ap_gastado_actuando += costo
        nodo.estado_fuego = EstadoFuego.LIMPIO
        self.model._marcar_nodo(nodo)
        self.registrar_accion(AgentAction.EXTINGUISH, objetivo)

    def _interactuar_celda_actual(self):
        nodo = self.model.mapa_nodos[self.pos]

        for item in list(nodo.contenido):
            if not isinstance(item, POI):
                continue

            item.revelado = True
            self.model.pois_reclamados.pop(self.pos, None)
            nodo.contenido.remove(item)
            self.model._marcar_nodo(nodo)

            if item.tipo == TipoPOI.FALSA_ALARMA:
                self.registrar_accion(AgentAction.SEARCH, self.pos)
            elif not self.llevando_victima:
                self.llevando_victima = True
                self.registrar_accion(AgentAction.PICK_UP_VICTIM, self.pos)
            else:
                nodo.contenido.append(item)

        if self.llevando_victima and self._es_salida(self.pos):
            self.llevando_victima = False
            self.model.victimas_salvadas += 1
            self.model._marcar_nodo(nodo)
            self.registrar_accion(AgentAction.RESCUE_VICTIM, self.pos)

    def _es_salida(self, pos):
        x, y = pos
        return (
            x == 0
            or x == self.model.grid.width - 1
            or y == 0
            or y == self.model.grid.height - 1
        )

    def _soltar_victima(self):
        if not self.llevando_victima:
            return

        self.llevando_victima = False
        nodo = self.model.mapa_nodos[self.pos]
        victima = POI(TipoPOI.VICTIMA)
        victima.revelado = True
        nodo.contenido.append(victima)
        self.model._marcar_nodo(nodo)
        self.registrar_accion(AgentAction.DROP_VICTIM, self.pos)


class Rescuer(RandomRescuer):
    def step(self):
        self._asignar_roles()
        if self.estado == AgentStatus.KNOCKED_DOWN:
            self.estado = AgentStatus.ACTIVE

        self._iniciar_turno()
        self._interactuar_celda_actual()

        while self.ap > 0:
            accion = self._accion_rescatista() if self.role == Role.SEARCHER else self._accion_soldado()
            if accion is None:
                legales = self._acciones_legales()
                if not legales:
                    break
                accion = random.choice(legales)
            self._ejecutar(accion)

        self._terminar_turno()

    def _asignar_roles(self):
        if getattr(self.model, "_roles_step", None) == self.model.steps:
            return
        self.model._roles_step = self.model.steps
        agentes = list(self.model.agents)
        fuegos = sum(n.estado_fuego == EstadoFuego.FUEGO for n in self.model.mapa_nodos.values())
        soldados = 0
        libres = [a for a in agentes if not a.llevando_victima]
        elegidos = set(libres[:soldados])
        for agente in agentes:
            agente.role = Role.SOLDIER if agente in elegidos else Role.SEARCHER

    def _ejecutar(self, accion):
        tipo, objetivo = accion
        if tipo == AgentAction.MOVE:
            self._mover(objetivo)
        elif tipo == AgentAction.OPEN_DOOR:
            self._abrir_puerta(objetivo)
        else:
            self._extinguir(objetivo)

    def _accion_rescatista(self):
        if not self.llevando_victima and self.ap >= 2:
            actual = self.model.mapa_nodos[self.pos]
            fuegos = [actual] if actual.estado_fuego == EstadoFuego.FUEGO else []
            fuegos.extend(
                vecino for vecino, arista in actual.vecinos.items()
                if vecino.estado_fuego == EstadoFuego.FUEGO
                and not (isinstance(arista, Muro) and arista.hp > 0)
                and not (isinstance(arista, Puerta) and arista.cerrado)
            )
            if fuegos:
                objetivo = max(fuegos, key=lambda nodo: self._riesgo(nodo.pos))
                return AgentAction.EXTINGUISH, objetivo.pos
        if not self.llevando_victima and self.ap >= 1:
            actual = self.model.mapa_nodos[self.pos]
            humos = [actual] if actual.estado_fuego == EstadoFuego.HUMO else []
            humos.extend(
                vecino for vecino, arista in actual.vecinos.items()
                if vecino.estado_fuego == EstadoFuego.HUMO
                and not (isinstance(arista, Muro) and arista.hp > 0)
                and not (isinstance(arista, Puerta) and arista.cerrado)
            )
            if humos:
                return AgentAction.EXTINGUISH, humos[0].pos
        if self.llevando_victima:
            return self._hacia(self._salidas(), evitar_fuego=True)
        pois = [
            pos for pos, nodo in self.model.mapa_nodos.items()
            if any(isinstance(item, POI) for item in nodo.contenido)
        ]
        rutas = [(len(ruta), pos) for pos in pois if (ruta := self._ruta([pos]))]
        if not rutas:
            return None
        minimo = min(costo for costo, _ in rutas)
        destinos = sorted(pos for costo, pos in rutas if costo <= minimo + 1)
        destinos = [destinos[self.unique_id % len(destinos)]]
        return self._hacia(destinos, evitar_fuego=self.llevando_victima)

    def _accion_soldado(self):
        fuegos = [pos for pos, nodo in self.model.mapa_nodos.items() if nodo.estado_fuego == EstadoFuego.FUEGO]
        if not fuegos:
            humos = [pos for pos, nodo in self.model.mapa_nodos.items() if nodo.estado_fuego == EstadoFuego.HUMO]
            return self._hacia(humos)

        rutas = []
        for fuego in fuegos:
            ruta = self._ruta([fuego], evitar_fuego=True, destino_fuego=True)
            if ruta:
                rutas.append((len(ruta), -self._riesgo(fuego), fuego))
        if not rutas:
            return None
        return self._hacia([min(rutas)[2]], evitar_fuego=True, destino_fuego=True)

    def _hacia(self, destinos, evitar_fuego=False, destino_fuego=False):
        if not destinos:
            return None
        ruta = self._ruta(destinos, evitar_fuego, destino_fuego)
        if not ruta:
            return None
        if len(ruta) == 1:
            nodo = self.model.mapa_nodos[ruta[0]]
            costo = 1 if nodo.estado_fuego == EstadoFuego.HUMO else 2
            if nodo.estado_fuego != EstadoFuego.LIMPIO and self.ap >= costo:
                return AgentAction.EXTINGUISH, ruta[0]
            return None

        siguiente = ruta[1]
        actual = self.model.mapa_nodos[self.pos]
        destino = self.model.mapa_nodos[siguiente]
        arista = actual.vecinos[destino]
        if isinstance(arista, Puerta) and arista.cerrado and self.ap >= 1:
            return AgentAction.OPEN_DOOR, siguiente
        if destino.estado_fuego != EstadoFuego.LIMPIO and self.ap >= (1 if destino.estado_fuego == EstadoFuego.HUMO else 2):
            return AgentAction.EXTINGUISH, siguiente
        costo = 2 if self.llevando_victima or destino.estado_fuego == EstadoFuego.FUEGO else 1
        if self.ap >= costo and not (self.llevando_victima and destino.estado_fuego == EstadoFuego.FUEGO):
            return AgentAction.MOVE, siguiente
        return None

    def _ruta(self, destinos, evitar_fuego=False, destino_fuego=False):
        destinos = set(destinos)
        cola = [(0, self.pos)]
        costos = {self.pos: 0}
        anterior = {self.pos: None}
        while cola:
            costo, pos = heapq.heappop(cola)
            if costo != costos[pos]:
                continue
            if pos in destinos:
                ruta = []
                while pos is not None:
                    ruta.append(pos)
                    pos = anterior[pos]
                return list(reversed(ruta))
            for vecino, arista in self.model.mapa_nodos[pos].vecinos.items():
                if isinstance(arista, Muro) and arista.hp > 0:
                    continue
                if evitar_fuego and vecino.estado_fuego == EstadoFuego.FUEGO and not (destino_fuego and vecino.pos in destinos):
                    continue
                paso = 2 if self.llevando_victima or vecino.estado_fuego == EstadoFuego.FUEGO else 1
                if isinstance(arista, Puerta) and arista.cerrado:
                    paso += 1
                nuevo = costo + paso
                if nuevo < costos.get(vecino.pos, float("inf")):
                    costos[vecino.pos] = nuevo
                    anterior[vecino.pos] = pos
                    heapq.heappush(cola, (nuevo, vecino.pos))
        return None

    def _riesgo(self, origen):
        cola = [origen]
        vistos = {origen}
        humo = 0
        muros = 0
        while cola:
            pos = cola.pop()
            for vecino, arista in self.model.mapa_nodos[pos].vecinos.items():
                if pos == origen and isinstance(arista, Muro) and arista.hp > 0:
                    muros += 3 if arista.hp == 1 else 1
                if isinstance(arista, Muro) and arista.hp > 0 or isinstance(arista, Puerta) and arista.cerrado:
                    continue
                if vecino.estado_fuego == EstadoFuego.FUEGO and vecino.pos not in vistos:
                    vistos.add(vecino.pos)
                    cola.append(vecino.pos)
                elif vecino.estado_fuego == EstadoFuego.HUMO:
                    humo += 1
        return len(vistos) * 4 + humo + muros * 8

    def _salidas(self):
        return [pos for pos in self.model.mapa_nodos if self._es_salida(pos)]
