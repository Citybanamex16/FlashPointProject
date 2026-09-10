using UnityEngine;

public class GameMaster : MonoBehaviour
{
    [Header("Referencias")]
    public GameView view; // Referencia a la Vista en escena
    public BoardBuilder boardBuilder; //Ref a Manager de Setup
    public BoardManager boardManager;
    private PythonApiService _apiService;

    private bool setupStarted = false;

    private void Awake()
    {
        _apiService = new PythonApiService();
    }


    private void Start(){

        InitMap();

    }



    async private void InitMap(){

        //1. Activamos Spinner
        view.SetLoadingState(true,setupStarted);

        //2. Solicitamos servicio de red 
        SetupDTO response = await _apiService.requestSetupDTO();

        if (response != null)
        {
            var (nodesMap, edgesMap) = boardBuilder.BuildInitialMap(response);
            setupStarted = true;
            boardManager.InitializeSimulation(nodesMap,edgesMap);

        }
        else
        {
            
            setupStarted = false;
        }

        view.SetLoadingState(false,setupStarted);

    }

}
