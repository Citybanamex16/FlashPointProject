using System.Collections;
using System.Collections.Generic;
using UnityEngine;


public class BoardBuilder : MonoBehaviour{

//Referencias de Prefabs//
[Header("Configuración de Grilla")]
public float cellSize = 10.0f;

[Header("Prefabs de assets")]
public GameObject tile;
public GameObject puerta;
public GameObject wall;

[Header("Referencias")]
public CameraController MainCamara;

private SetupDTO _lastSetupData;

    // Start is called before the first frame update
    void Start()
    {
        
    }

    // Update is called once per frame
    void Update()
    {
        
    }



    public void BuildInitialMap(SetupDTO Setupdata){
        print("Generating map...");
        Setupdata.ImprimirResumen();

        _lastSetupData = Setupdata;

        ConstruirNodos(Setupdata);

        ConstruirAristas(Setupdata);

        MainCamara.AdjustCameraToBoard(Setupdata.width, Setupdata.height, cellSize);

    }


    private void ConstruirNodos(SetupDTO setupData)
    {
        // Acceso directo a la lista setupData.nodes
        foreach (NodeDTO nodeData in setupData.nodes)
        {
            // Calculamos la posición en mundo usando la matemática del CELL_SIZE
            Vector3 position = GetWorldPosition(nodeData.x, nodeData.y);

            // Instanciamos el Prefab visual de la casilla
            GameObject nodeGO = Instantiate(tile, position, Quaternion.identity, transform);
            nodeGO.name = $"Node_({nodeData.x},{nodeData.y})";
        }
    }

    private void ConstruirAristas(SetupDTO setupData)
    {
        // Acceso directo a la lista setupData.edges
        foreach (EdgeDTO edgeData in setupData.edges)
        {
            // 1. Obtener posiciones en mundo de ambos nodos extremos
            Vector3 posA = GetWorldPosition(edgeData.posA.x, edgeData.posA.y);
            Vector3 posB = GetWorldPosition(edgeData.posB.x, edgeData.posB.y);

            // 2. Calcular Punto Medio exacto para colocar el Muro/Puerta
            Vector3 middlePosition = (posA + posB) / 2.0f;

            // 3. Calcular Rotación basada en si la alineación es horizontal o vertical
            bool esMuroVertical = edgeData.posA.x != edgeData.posB.x;
            Quaternion rotation = esMuroVertical ? Quaternion.Euler(0, 90f, 0) : Quaternion.identity;

            // 4. Seleccionar Prefab correcto según el Enum DTO ("MURO" o "PUERTA")
            GameObject prefabToSpawn = (edgeData.tipo == "PUERTA") ? tile : wall;

            // 5. Instanciar en la escena
            GameObject edgeGO = Instantiate(prefabToSpawn, middlePosition, rotation, transform);
            edgeGO.name = $"Edge_{edgeData.tipo}_({edgeData.posA.x},{edgeData.posA.y})-({edgeData.posB.x},{edgeData.posB.y})";
        }
    }

    /// <summary>
    /// Helper para traducir coordenadas discretas (x,y) a posición flotante en Unity.
    /// </summary>
    private Vector3 GetWorldPosition(int x, int y)
    {
        return new Vector3(x * cellSize, 0f, y * cellSize);
    }


/// ===== Debug en Gizmos de inicializacion  basado en motor de dibujo de unity ===

    /// <summary>
    /// Dibuja formas nativas en la vista de Scene para verificar la matemática del DTO.
    /// </summary>
    private void OnDrawGizmos()
    {
        if (_lastSetupData == null) return;

        // 1. DIBUJAR PUNTOS DE NODOS (Esferas Azules)
        if (_lastSetupData.nodes != null)
        {
            Gizmos.color = Color.cyan;
            foreach (var node in _lastSetupData.nodes)
            {
                Vector3 pos = GetWorldPosition(node.x, node.y);
                Gizmos.DrawSphere(pos, 0.15f * cellSize);
                
                // Malla guía para el piso de la casilla
                Gizmos.DrawWireCube(pos, new Vector3(cellSize, 0.05f, cellSize));
            }
        }

        // 2. DIBUJAR PUNTOS Y LÍNEAS DE ARISTAS (Líneas y Cajas Rojas/Amarillas)
        if (_lastSetupData.edges != null)
        {
            foreach (var edge in _lastSetupData.edges)
            {
                Vector3 posA = GetWorldPosition(edge.posA.x, edge.posA.y);
                Vector3 posB = GetWorldPosition(edge.posB.x, edge.posB.y);
                Vector3 midPos = (posA + posB) / 2.0f;

                bool esMuroVertical = edge.posA.x != edge.posB.x;

                // Color según tipo
                Gizmos.color = (edge.tipo == "PUERTA") ? Color.yellow : Color.red;

                // Línea de conexión entre nodos
                Gizmos.DrawLine(posA, posB);

                // Indicador del volumen del Muro/Puerta
                Vector3 size = esMuroVertical 
                    ? new Vector3(0.1f, 0.8f, cellSize)  // Orientación en Z
                    : new Vector3(cellSize, 0.8f, 0.1f); // Orientación en X

                Gizmos.DrawWireCube(midPos + new Vector3(0, 0.4f, 0), size);
            }
        }
    }


}
