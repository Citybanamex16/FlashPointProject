using UnityEngine;
using UnityEngine.UI;
using TMPro; // Usamos TextMeshPro, el estándar moderno de UI en Unity

public class GameView : MonoBehaviour
{
    [Header("Inputs")]
    [SerializeField] private TMP_InputField nameInput;
    [SerializeField] private TMP_InputField scoreInput;

    [Header("UI Controls")]
    [SerializeField] private Button sendButton;
    [SerializeField] private TMP_Text statusText;

    // Propiedades públicas para que el Controlador lea los valores ingresados
    public string PlayerName => nameInput.text;
    public int Score => int.TryParse(scoreInput.text, out int val) ? val : 0;
    public Button SendButton => sendButton;

    public void DisplayStatus(string message)
    {
        statusText.text = message;
    }

    public void SetLoadingState(bool isLoading)
    {
        sendButton.interactable = !isLoading;
        statusText.text = isLoading ? "Procesando en Python..." : statusText.text;
    }
}