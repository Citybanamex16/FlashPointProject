using UnityEngine;
using UnityEngine.UI;
using TMPro; // Usamos TextMeshPro, el estándar moderno de UI en Unity

public class GameView : MonoBehaviour
{

    [Header("UI Elements")]
    [SerializeField] private TMP_Text statusText;

    public void SetLoadingState(bool isLoading)
    {
        if(isLoading){
            statusText.text = "Loading...";
        }
        else{
            statusText.text = "¡Ready!";
        }
    }
}