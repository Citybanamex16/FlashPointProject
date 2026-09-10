using UnityEngine;
using UnityEngine.UI;
using TMPro; // Usamos TextMeshPro, el estándar moderno de UI en Unity

public class GameView : MonoBehaviour
{

    [Header("UI Elements")]
    [SerializeField] private TMP_Text statusText;
    [SerializeField] private  Button initButton;


    private void Awake(){
        if(initButton != false){
            initButton.gameObject.SetActive(false);
        }
    }


    public void SetLoadingState(bool isLoading,bool success)
    {
        if(isLoading){
            statusText.text = "Loading...";
        }
        else{
            if(success){
                statusText.text = "¡Ready!";
                initButton.gameObject.SetActive(true);
            }
            else{
                statusText.text = "Error, check log";
            }
        }
    }

    public void hideButton(){
        initButton.gameObject.SetActive(false);
    }
}