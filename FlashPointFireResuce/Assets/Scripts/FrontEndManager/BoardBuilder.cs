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



    public (Dictionary<Vector2Int, NodeView> nodesMap, Dictionary<string, EdgeView> edgesMap) BuildInitialMap(SetupDTO setupData)
    {
        _lastSetupData = setupData;

        var nodesMap = ConstruirNodos(setupData);
        var edgesMap = ConstruirAristas(setupData);

        MainCamara.AdjustCameraToBoard(setupData.width, setupData.height, cellSize);

        return (nodesMap, edgesMap);
    }


    private Dictionary<Vector2Int, NodeView> ConstruirNodos(SetupDTO setupData)
    {
        var nodeViews = new Dictionary<Vector2Int, NodeView>();

        foreach (NodeDTO nodeData in setupData.nodes)
        {
            Vector3 position = GetWorldPosition(nodeData.x, nodeData.y);
            GameObject nodeGO = Instantiate(tile, position, Quaternion.identity, transform);
            nodeGO.name = $"Node_({nodeData.x},{nodeData.y})";

            // Extraemos el Script del prefab para poder manipularlo.
            NodeView nodeView = nodeGO.GetComponent<NodeView>();
            if (nodeView != null)
            {
                nodeView.SetInitialState(nodeData);
                nodeViews.Add(new Vector2Int(nodeData.x, nodeData.y), nodeView);
            }
        }
        return nodeViews;
    }

    private Dictionary<string, EdgeView> ConstruirAristas(SetupDTO setupData)
    {
        var edgeViews = new Dictionary<string, EdgeView>();

        foreach (EdgeDTO edgeData in setupData.edges)
        {
            Vector3 posA = GetWorldPosition(edgeData.posA.x, edgeData.posA.y);
            Vector3 posB = GetWorldPosition(edgeData.posB.x, edgeData.posB.y);
            Vector3 middlePosition = (posA + posB) / 2.0f;
            
            bool esMuroVertical = edgeData.posA.x != edgeData.posB.x;
            Quaternion rotation = esMuroVertical ? Quaternion.Euler(0, 90f, 0) : Quaternion.identity;

            GameObject prefabToSpawn = (edgeData.tipo == "PUERTA") ? puerta : wall;
            GameObject edgeGO = Instantiate(prefabToSpawn, middlePosition, rotation, transform);

            // Generamos una clave única en texto: "0,1-1,1"
            string edgeKey = GetEdgeKey(edgeData.posA.x, edgeData.posA.y, edgeData.posB.x, edgeData.posB.y);
            edgeGO.name = $"Edge_{edgeData.tipo}_[{edgeKey}]";

            EdgeView edgeView = edgeGO.GetComponent<EdgeView>();
            if (edgeView != null)
            {
                edgeView.SetInitialState(edgeData);
                edgeViews.Add(edgeKey, edgeView);
            }
        }
        return edgeViews;
    }

    /// <summary>
    /// Helper para traducir coordenadas discretas (x,y) a posición flotante en Unity.
    /// </summary>
    private Vector3 GetWorldPosition(int x, int y)
    {
        return new Vector3(x * cellSize, 0f, y * cellSize);
    }

    public string GetEdgeKey(int x1, int y1, int x2, int y2) => $"{x1},{y1}-{x2},{y2}";


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
