import random
import unittest
from unittest.mock import patch

from agents import AgentAction, Rescuer
from core_types import EstadoFuego, Muro, POI, Puerta, TipoPOI
from model import FlashPointModel


class RulesTest(unittest.TestCase):
    def setUp(self):
        random.seed(1)
        self.model = FlashPointModel(6, 10, 8, verbose=False)

    def test_tracker_conserves_markers(self):
        tracker = self.model._poi_tracker_dto()
        self.assertEqual(sum(tracker["victimas"].values()), 10)
        self.assertEqual(sum(tracker["falsas_alarmas"].values()), 5)

    def test_carried_victim_counts_as_active_poi(self):
        agent = next(iter(self.model.agents))
        agent.llevando_victima = True
        poi = next(
            item for nodo in self.model.mapa_nodos.values()
            for item in nodo.contenido if isinstance(item, POI)
        )
        self.model.mapa_nodos[next(
            pos for pos, nodo in self.model.mapa_nodos.items() if poi in nodo.contenido
        )].contenido.remove(poi)
        before = len(self.model.bolsa_poi)
        self.model._reponer_pois()
        self.assertEqual(len(self.model.bolsa_poi), before)

    def test_poi_cleans_hazard_next_to_fire(self):
        for nodo in self.model.mapa_nodos.values():
            nodo.contenido = [item for item in nodo.contenido if not isinstance(item, POI)]
        self.model.bolsa_poi = [TipoPOI.VICTIMA]
        self.model.mapa_nodos[(2, 2)].estado_fuego = EstadoFuego.FUEGO
        self.model.mapa_nodos[(2, 3)].estado_fuego = EstadoFuego.FUEGO
        with patch("model.random.randint", side_effect=[2, 2]):
            self.model._reponer_pois()
        nodo = self.model.mapa_nodos[(2, 2)]
        self.assertEqual(nodo.estado_fuego, EstadoFuego.LIMPIO)
        self.assertTrue(any(isinstance(item, POI) for item in nodo.contenido))

    def test_exterior_fire_is_removed(self):
        nodo = self.model.mapa_nodos[(0, 2)]
        nodo.estado_fuego = EstadoFuego.FUEGO
        self.model._limpiar_fuego_exterior()
        self.assertEqual(nodo.estado_fuego, EstadoFuego.LIMPIO)
        self.assertIn(nodo.pos, self.model.nodos_afectados)

    def test_random_agent_cannot_finish_entry_into_fire(self):
        agent = next(iter(self.model.agents))
        destino = next(
            vecino for vecino, arista in self.model.mapa_nodos[agent.pos].vecinos.items()
            if arista is None
        )
        destino.estado_fuego = EstadoFuego.FUEGO
        agent.ap = 3
        self.assertNotIn((AgentAction.MOVE, destino.pos), agent._acciones_legales())
        agent.ap = 4
        agent._mover(destino.pos)
        self.assertEqual(agent._acciones_legales(), [(AgentAction.EXTINGUISH, agent.pos)])

    def test_strategic_agent_clears_smoke_before_moving(self):
        agent = next(iter(self.model.agents))
        destino = next(
            vecino for vecino, arista in self.model.mapa_nodos[agent.pos].vecinos.items()
            if arista is None
        )
        destino.estado_fuego = EstadoFuego.HUMO
        self.assertEqual(agent._hacia([destino.pos]), (AgentAction.EXTINGUISH, destino.pos))

    def test_seventh_rescue_stops_before_fire(self):
        agent = next(iter(self.model.agents))
        self.model.victimas_salvadas = 6
        agent.llevando_victima = True
        self.model.step()
        self.assertEqual(self.model.estado_juego, "VICTORIA")
        self.assertIsNone(self.model.ultima_tirada)

    def test_collapse_records_board_and_carried_victims(self):
        agent = next(iter(self.model.agents))
        agent.llevando_victima = True
        before = self.model.victimas_perdidas
        board_victims = sum(
            item.tipo == TipoPOI.VICTIMA
            for nodo in self.model.mapa_nodos.values()
            for item in nodo.contenido if isinstance(item, POI)
        )
        self.model.marcadores_dano = 0
        self.model.evaluar_estado_juego()
        self.assertEqual(self.model.victimas_perdidas, before + board_victims + 1)
        self.assertFalse(any(a.llevando_victima for a in self.model.agents))
        self.assertEqual(self.model._poi_tracker_dto()["activos"], 0)

    def test_collapse_stops_explosion_immediately(self):
        origen = self.model.mapa_nodos[(5, 2)]
        origen.estado_fuego = EstadoFuego.FUEGO
        self.model.marcadores_dano = 1
        hp_antes = sum(
            arista.hp for arista in self.model.mapa_aristas.values()
            if isinstance(arista, Muro)
        )
        self.model._resolver_explosion(origen)
        hp_despues = sum(
            arista.hp for arista in self.model.mapa_aristas.values()
            if isinstance(arista, Muro)
        )
        self.assertEqual(hp_antes - hp_despues, 1)
        self.assertEqual(self.model.estado_juego, "DERROTA")

    def test_fourth_lost_victim_skips_replenishment(self):
        for nodo in self.model.mapa_nodos.values():
            nodo.contenido = [item for item in nodo.contenido if not isinstance(item, POI)]
        nodo = self.model.mapa_nodos[(4, 4)]
        nodo.estado_fuego = EstadoFuego.FUEGO
        nodo.contenido.append(POI(TipoPOI.VICTIMA))
        self.model.victimas_perdidas = 3
        bolsa = len(self.model.bolsa_poi)

        def avanzar():
            return None

        with patch.object(Rescuer, "step"), patch.object(self.model, "avanzar_fuego", avanzar):
            self.model.step()
        self.assertEqual(self.model.estado_juego, "DERROTA")
        self.assertEqual(len(self.model.bolsa_poi), bolsa)

    def test_destroyed_door_is_in_delta(self):
        puerta = next(arista for arista in self.model.mapa_aristas.values() if isinstance(arista, Puerta))
        puerta.destruir()
        self.model._marcar_arista(puerta)
        edge = self.model.get_step_dto()["edges"][0]
        self.assertTrue(edge["destruida"])
        self.assertFalse(edge["cerrado"])

    def test_dice_roll_is_in_delta(self):
        with patch("model.random.randint", side_effect=[4, 3]):
            self.model.avanzar_fuego()
        self.assertEqual(self.model.get_step_dto()["tirada_dados"], {"x": 4, "y": 3})


if __name__ == "__main__":
    unittest.main()
