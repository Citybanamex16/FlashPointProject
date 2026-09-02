using UnityEngine;
using UnityEngine.UI;
using TMPro; // Usamos TextMeshPro, el estándar moderno de UI en Unity

public class GameView : MonoBehaviour
{

    [Header("UI Elements")]
    [SerializeField] private TMP_Text statusText;

    public void SetLoadingState(bool isLoading)
    {
        statusText.text = isLoading ? "Procesando en Python..." : statusText.text;
    }
}