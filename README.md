# FlashPoint: Zombie Escape

## Descripción General
Este proyecto contiene una simulación de sistemas multiagente basada en el juego de mesa *Flash Point: Fire Rescue*, desarrollada para la materia de **Modelación de Sistemas Multiagentes**. Adaptamos el juego para que tenga una narrativa de zombies, por lo cual, nuestro proyecto se llama FLashPoint: Zombie Escape. El proyecto modela agentes Rescatistas autónomos que colaboran en un entorno dinámico y peligroso para rescatar víctimas, mientras gestionan el daño estructural del inmueble y la propagación de infecciones y amenazas.

**Autores:**
* Carlos Delgado Contreras (A01712819)
* Lucca Traslosheros Abascal (A01713944)
* Oscar Lopez Cardoso (A01713355)

---

## Aspectos Técnicos Destacados

### 1. Discretización del Mapa (Dígrafo Dinámico)
* **Topología del Tablero**: Representación de una cuadrícula de 10 casillas horizontales por 8 verticales (80 casillas).
* **Estructura de Datos**: Uso de un dígrafo ponderado dinámico con un diccionario de adyacencia orientado a objetos para modelar los nodos (casillas) y aristas (bordes, muros y puertas).
* **Integridad Referencial**: Dos nodos adyacentes comparten la referencia al mismo objeto `Arista` sin duplicación de datos, garantizando la sincronización de estados en tiempo real.
* **Costo Dinámico de Navegación**: El costo en Puntos de Acción (AP) para el desplazamiento se calcula con la fórmula:
  $$\text{Costo Total} = \text{Arista.obtenerCosto()} + \text{NodoDestino.obtenerCosto()}$$
  Esto permite que los algoritmos de navegación (Pathfinding) contemplen la opción de demoler muros (4 AP) versus rodearlos si implica un recorrido mayor.

### 2. Arquitectura de Agentes y Toma de Decisiones
Los agentes funcionan mediante una Máquina de Estados Finitos (FSM) jerárquica guiada por objetivos principales, roles tácticos y reglas globales:

| Nivel | Componente | Descripción |
| :--- | :--- | :--- |
| **Estados Primarios** | `SEARCH` | El agente evalúa la distancia a los Puntos de Interés (POIs) activos y navega hacia el más accesible para revelar/recolectar víctimas. |
| | `ESCAPE` | Se activa al cargar una víctima (`cargando víctima == True`); calcula la ruta óptima hacia la salida más cercana considerando penalizaciones. |
| **Estados Secundarios (Roles)** | `Searcher` | Prioriza pasillos despejados para maximizar la velocidad de localización y evacuación de víctimas. |
| | `Wallbreaker` | Cuenta con reducción en el costo de AP para picar muros, creando vías rápidas de evacuación. |
| | `Soldier` | Se enfoca en la contención de spores y amenazas (Zombies/Esporas) para despejar el paso al equipo. |
| **Reglas Universales** | Preservación Estructural | Anula cualquier comportamiento de rol: si el daño de la casa alcanza el umbral crítico ($\ge 18$ marcadores de daño acumulados de 24 máx.), se desactiva la habilidad de demolición para prevenir el colapso. |

---

## Flujo del Juego y Condiciones de Victoria/Derrota

La simulación se ejecuta en un ciclo continuo de tres fases:

1. **Fase Jugador**: Los agentes gastan Puntos de Acción (AP) para desplazarse, matar esporas, romper muros o transportar víctimas.
2. **Fase Expansion**: Tirada de dados (D6-D6) para determinar la expansión de esporas, explosiones y daño estructural a los muros.
3. **Fase POIs**: Evaluación del tablero y generación de nuevos POIs si los activos son < 3.

### Condiciones de Fin de Juego
* **Victoria**: Lograr evacuar con éxito a 7 víctimas.
* **Derrota**: Acumular más de 4 víctimas perdidas o alcanzar 24 puntos de daño estructural en los muros.

---

## Interfaz de Usuario y Assets

* **Diseño UI**: Panel lateral que muestra en tiempo real la salud estructural del inmueble (máx. 24), contador de víctimas (rescatadas/perdidas), la ronda/fase actual y la reserva de APs de cada agente.
* **Assets 3D**: Incluye modelos tridimensionales para muros modulares, esporas/humo, agentes bomberos, víctimas y zombies.
