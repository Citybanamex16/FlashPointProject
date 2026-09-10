"""
metrics.py - Medición y ejecución de múltiples partidas.
"""

import random

import pandas as pd
from mesa.datacollection import DataCollector

from core_types import EstadoFuego, POI, Muro, Puerta
from model import FlashPointModel


# ============================================================
# CONTADORES
# ============================================================

def _contar_estado_fuego(model, estado):
    return sum(
        1
        for nodo in model.mapa_nodos.values()
        if nodo.estado_fuego == estado
    )


def _iterar_aristas_unicas(model):
    procesadas = set()

    for nodo in model.mapa_nodos.values():
        for _vecino, arista in nodo.vecinos.items():
            if arista is not None and arista not in procesadas:
                procesadas.add(arista)
                yield arista


def _contar_paredes(model):
    intactos = 0
    danados = 0
    destruidos = 0

    for arista in _iterar_aristas_unicas(model):
        if isinstance(arista, Muro):
            if arista.hp == 2:
                intactos += 1
            elif arista.hp == 1:
                danados += 1
            else:
                destruidos += 1

    return intactos, danados, destruidos


def _contar_puertas(model):
    abiertas = 0
    cerradas = 0

    for arista in _iterar_aristas_unicas(model):
        if isinstance(arista, Puerta):
            if arista.cerrado:
                cerradas += 1
            else:
                abiertas += 1

    return abiertas, cerradas


def _contar_pois(model):
    activos = 0
    revelados = 0

    for nodo in model.mapa_nodos.values():
        for item in nodo.contenido:
            if isinstance(item, POI):
                activos += 1

                if item.revelado:
                    revelados += 1

    return activos, revelados


# ============================================================
# DATA COLLECTOR
# ============================================================

def build_collector():

    def _walls(model):
        return _contar_paredes(model)

    def _pois(model):
        return _contar_pois(model)

    return DataCollector(
        model_reporters={
            "Steps": lambda m: m.steps,
            "DamageMarkers": lambda m: m.marcadores_dano,
            "VictimsSaved": lambda m: m.victimas_salvadas,
            "VictimsLost": lambda m: m.victimas_perdidas,
            "GameState": lambda m: m.estado_juego,
            "FireCells": lambda m: _contar_estado_fuego(
                m,
                EstadoFuego.FUEGO
            ),
            "WallsDestroyed": lambda m: _walls(m)[2],
            "ActivePOIs": lambda m: _pois(m)[0],
        },

        agent_reporters={
            "Role": lambda a: a.role.value,
            "CarryingVictim": lambda a: a.llevando_victima,
            "AP_Remaining": lambda a: a.ap,
            "Saved_AP": lambda a: a.saved_ap,
        }
    )


class MeasuredFlashPointModel(FlashPointModel):
    """Modelo FlashPoint con recolección de métricas."""

    def __init__(self, **kwargs):
        # No imprimir eventos durante batch runs
        kwargs["verbose"] = False

        super().__init__(**kwargs)

        self.datacollector = build_collector()
        self.datacollector.collect(self)

    def step(self):
        super().step()
        self.datacollector.collect(self)


# ============================================================
# EJECUTAR UNA PARTIDA
# ============================================================

def ejecutar_partida(
    game_number,
    total_games,
    max_steps=300,
    seed=None
):
    """
    Ejecuta una partida completa y muestra su resultado.
    """

    if seed is not None:
        random.seed(seed)

    model = MeasuredFlashPointModel(
        numAgents=4,
        width=10,
        height=8,
    )

    steps = 0

    while (
        model.estado_juego == "EN_CURSO"
        and steps < max_steps
    ):
        model.step()
        steps += 1

    # Determinar resultado
    estado = model.estado_juego

    if estado == "VICTORIA":
        resultado = "VICTORIA"
    elif estado == "DERROTA":
        resultado = "DERROTA"
    else:
        resultado = "LIMITE"

    # print(
    #     f"Game {game_number:>2}/{total_games} | "
    #     f"{resultado:<8} | "
    #     f"{steps:>3} turns | "
    #     f"Saved: {model.victimas_salvadas} | "
    #     f"Lost: {model.victimas_perdidas}"
    # )

    return model


# ============================================================
# BATCH RUN
# ============================================================

def ejecutar_batch(
    num_games=1000,
    max_steps=300,
    base_seed=None
):
    """
    Ejecuta múltiples partidas y muestra estadísticas generales.
    """

    print("=" * 60)
    print(f"RUNNING {num_games} GAMES")
    print(f"BASE SEED:  {base_seed}")
    print("=" * 60)

    modelos = []

    for game_number in range(1, num_games + 1):
        game_seed = (
            None
            if base_seed is None
            else base_seed + game_number - 1
        )
        model = ejecutar_partida(
            game_number,
            num_games,
            max_steps,
            seed=game_seed
        )

        modelos.append((game_seed, model))

    # --------------------------------------------------------
    # Crear DataFrame con resultados finales
    # --------------------------------------------------------

    resultados = []

    for game_seed, model in modelos:
        resultados.append({
            "Seed": game_seed,
            "Steps": model.steps,
            "DamageMarkers": model.marcadores_dano,
            "VictimsSaved": model.victimas_salvadas,
            "VictimsLost": model.victimas_perdidas,
            "GameState": model.estado_juego,
            "FireCells": _contar_estado_fuego(
                model,
                EstadoFuego.FUEGO
            ),
            "WallsDestroyed": _contar_paredes(model)[2],
            "ActivePOIs": _contar_pois(model)[0],
        })

    df = pd.DataFrame(resultados)

    # ========================================================
    # RESUMEN
    # ========================================================

    victories = (df["GameState"] == "VICTORIA").sum()
    defeats = (df["GameState"] == "DERROTA").sum()
    limits = (df["GameState"] == "LIMITE").sum()

    win_rate = (victories / num_games) * 100

    print()
    print("=" * 60)
    print("BATCH SUMMARY")
    print("=" * 60)

    print(f"Games:       {num_games}")
    print(f"Victories:   {victories}")
    print(f"Defeats:     {defeats}")
    print(f"Limit:       {limits}")
    print(f"Win rate:    {win_rate:.1f}%")

    print()
    print(f"Avg turns:   {df['Steps'].mean():.1f}")
    print(f"Avg saved:   {df['VictimsSaved'].mean():.2f}")
    print(f"Avg lost:    {df['VictimsLost'].mean():.2f}")
    print(f"Avg damage:  {df['DamageMarkers'].mean():.2f}")
    print(f"Avg fire:    {df['FireCells'].mean():.2f}")
    print(
        f"Avg walls destroyed: "
        f"{df['WallsDestroyed'].mean():.2f}"
    )

    print("=" * 60)

    return df


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    df_batch = ejecutar_batch(
        num_games=1000,
        max_steps=300,
        base_seed=20260910
    )

    print()
    print("FINAL RESULTS:")
    print(df_batch)