using UnityEngine;
using UnityEngine.UI;
using TMPro; // Usamos TextMeshPro, el estándar moderno de UI en Unity

public class GameView : MonoBehaviour
{

    [Header("UI Elements")]
    [SerializeField] private TMP_Text statusText;
    [SerializeField] private  Button initButton;

    [SerializeField] private  TMP_Text houseLife; //house 23/24 format
    [SerializeField] private  TMP_Text diceRoll; // dice roll (x,y) format
    [SerializeField] private  Image victimsProgressBar; // progress bar vertical incremental

    [Header("Configuración de Reglas de Juego")]
    [SerializeField] private int maxDamageMarkers = 24; // Límite de daño antes de perder
    [SerializeField] private int maxVictimsToSave = 7;  // Víctimas necesarias para ganar



    private void Awake(){
        if(initButton != false){
            initButton.gameObject.SetActive(false);
        }

        houseLife.gameObject.SetActive(false);
        diceRoll.gameObject.SetActive(false);
        victimsProgressBar.gameObject.SetActive(false);

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
        statusText.gameObject.SetActive(false);

        houseLife.gameObject.SetActive(true);
        diceRoll.gameObject.SetActive(true);
        victimsProgressBar.gameObject.SetActive(true);
    }



    // === Apis para game Builder == //

    public void UpdateGUI(StepDTO stepDTO){
        if (stepDTO == null) return;

        // 1. Salud de la Casa (Daño estructural restante)
        if (houseLife != null)
        {
            int currentHP = Mathf.Max(0, stepDTO.marcadores_dano);
            houseLife.text = $"Structure: {currentHP}/{maxDamageMarkers}";
        }

        // 2. Tirada de Dados (Coordenadas de reaparición/fuego)
        if (diceRoll != null)
        {
            if (stepDTO.tirada_dados != null)
            {
                diceRoll.text = $"Dice Roll: ({stepDTO.tirada_dados.x}, {stepDTO.tirada_dados.y})";
            }
            else
            {
                diceRoll.text = "Dice Roll: (- , -)";
            }
        }

        // 3. Barra de Progreso de Víctimas Salvadas
        if (victimsProgressBar != null)
        {
            // Mapeamos el valor entre 0.0f y 1.0f para el Fill Amount de la Image
            float progress = (float)stepDTO.victimas_salvadas / maxVictimsToSave;
            victimsProgressBar.fillAmount = Mathf.Clamp01(progress);
        }
    }
}




