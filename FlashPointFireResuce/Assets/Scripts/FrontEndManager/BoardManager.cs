using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Threading.Tasks;


public class BoardManager : MonoBehaviour{

    private PythonApiService apiService;

    [Header("Configuración de Simulación")]
    public float stepDelay = 2.0f;
    public bool autoStep = true;
    public BoardBuilder boardBuilder;

    [Header("Referencias")]
    public GameView viewRef;

    // Diccionarios de referencia a las Vistas de la escena
    private Dictionary<Vector2Int, NodeView> _nodeViews;
    private Dictionary<string, EdgeView> _edgeViews;
    private Dictionary<int, AgentView> _agentViews;

    private void Awake()
    {
        apiService = new PythonApiService();
    }

    /// <summary>
    /// Llamado por el GameMaster/GameController tras recibir el SetupDTO inicial.
    /// </summary>

    public void InitializeSimulation(Dictionary<Vector2Int, NodeView> nodesMap, Dictionary<string, EdgeView> edgesMap,Dictionary<int, AgentView> agentsMap){
        print("Initializing Simulation");
        _nodeViews = nodesMap;
        _edgeViews = edgesMap;
        _agentViews = agentsMap;

        // 2. Iniciamos el bucle de ticks HTTP
        if (autoStep)
        {
            StartCoroutine(SimulationLoop());
        }
    }

   private IEnumerator SimulationLoop(){
    while (autoStep){
        yield return new WaitForSeconds(stepDelay);

        // 1. Creamos la tarea de la API
        Task<StepDTO> apiTask = apiService.requestStepDTO();

        // 2. Le decimos a la corrutina que espere a que la tarea termine
        yield return new WaitUntil(() => apiTask.IsCompleted);

        // 3. Cuando llega aquí, la tarea ya terminó. Obtenemos el resultado.
        StepDTO stepDTO = apiTask.Result;

        // 3.5 Actualizamos GUI
        viewRef.UpdateGUI(stepDTO);

        // 4. Aplicamos los cambios si el modelo es válido
        if (stepDTO != null)
        {   
            StartCoroutine(ApplyStepUpdatesRoutine(stepDTO));
        }
    }
}


    /// <summary>
    /// Sincroniza la vista de Unity con los cambios del StepDTO de Python.
    /// </summary>
    private IEnumerator ApplyStepUpdatesRoutine(StepDTO stepDTO){
    // STEP 1: Animamos y movemos a los agentes PRIMERO
    foreach (var agentData in stepDTO.agents)
    {
        if (_agentViews.TryGetValue(agentData.id, out AgentView agentView))
        {
            agentView.UpdateState(agentData);

            // ESPERA: Pausamos la ejecución hasta que el agente termine toda su cola de animación
            while (agentView.IsAnimating)
            {
                yield return null; // Espera al siguiente frame
            }
        }
    }

    // Pequeña pausa dramática para impacto visual
    yield return new WaitForSeconds(0.15f);

    // STEP 2: Actualizamos los NODOS (Fuego, Infección, Víctimas)
    foreach (var nodeData in stepDTO.nodes)
    {
        Vector2Int key = new Vector2Int(nodeData.x, nodeData.y);
        if (_nodeViews.TryGetValue(key, out NodeView view))
        {
            view.UpdateState(nodeData);
        }
    }

    // STEP 3: Actualizamos las ARISTAS (Muros rotos, Puertas)
    foreach (var edgeData in stepDTO.edges)
    {
        string key = boardBuilder.GetEdgeKey(edgeData.posA.x, edgeData.posA.y, edgeData.posB.x, edgeData.posB.y);
        if (_edgeViews.TryGetValue(key, out EdgeView view))
        {
            view.UpdateState(edgeData);
        }
    }
}
}
