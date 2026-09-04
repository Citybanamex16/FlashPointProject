using UnityEngine;

public class GameMaster : MonoBehaviour
{
    [Header("Referencias")]
    public GameView view; // Referencia a la Vista en escena
    public BoardBuilder boardBuilder; //Ref a Manager de Setup
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
        view.SetLoadingState(true);

        //2. Solicitamos servicio de red 
        SetupDTO response = await _apiService.requestSetupDTO();

        //3. Quitamos el spinner y evaluamos Inicializacion
        view.SetLoadingState(false);

        if (response != null)
        {
            boardBuilder.BuildInitialMap(response);
            setupStarted = true;
        }
        else
        {
            
            setupStarted = false;
        }

        view.SetLoadingState(false);

    }

}
