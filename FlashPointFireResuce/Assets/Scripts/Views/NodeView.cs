using UnityEngine;

public class NodeView : MonoBehaviour
{
    [Header("Referencias a Assets Visuales")]
    [SerializeField] private SpriteRenderer fuegoRenderer;
    [SerializeField] private GameObject victimaIcono;
    [SerializeField] private GameObject falsaAlarmaIcono;

    /// <summary>
    /// Configura el aspecto visual del nodo la primera vez.
    /// </summary>
    public void SetInitialState(NodeDTO dto)
    {
        UpdateState(dto);
    }

    /// <summary>
    /// Cambia los sprites/efectos según la información que llega de Python.
    /// </summary>
    public void UpdateState(NodeDTO dto)
    {
        // 1. Cambiar visual del Fuego (LIMPIO, HUMO, FUEGO)
        switch (dto.fuego)
        {
            case "LIMPIO":
                fuegoRenderer.enabled = false;
                break;
            case "HUMO":
                fuegoRenderer.enabled = true;
                fuegoRenderer.color = Color.gray;
                break;
            case "FUEGO":
                fuegoRenderer.enabled = true;
                fuegoRenderer.color = Color.red;
                break;
        }

        // 2. Cambiar visual del POI si existe
        if (dto.poi != null)
        {
            victimaIcono.SetActive(dto.poi.tipo == "VICTIMA");
            falsaAlarmaIcono.SetActive(dto.poi.tipo == "FALSA_ALARMA");
        }
        else
        {
            victimaIcono.SetActive(false);
            falsaAlarmaIcono.SetActive(false);
        }
    }
}