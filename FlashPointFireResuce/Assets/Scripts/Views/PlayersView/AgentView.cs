using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class AgentView : MonoBehaviour
{
    [Header("Configuración de Animación")]
    [SerializeField] private float moveSpeed = 4f;
    [SerializeField] private Transform modelContainer; // Referencia al objeto hijo "Visuals"

    private Queue<IEnumerator> _actionQueue = new Queue<IEnumerator>();
    private bool _isAnimating = false;
    public bool IsAnimating => _isAnimating || _actionQueue.Count > 0;

    public void SetInitialState(AgentDTO dto)
    {
        // Posicionamiento instantáneo al iniciar
        transform.position = GetWorldPosition(dto.posicion.x, dto.posicion.y);
    }

    public void UpdateState(AgentDTO dto)
    {
        if (dto.eventos_turno != null && dto.eventos_turno.Count > 0)
        {
            foreach (var actionEvent in dto.eventos_turno)
            {
                EnqueueAction(actionEvent.accion, actionEvent.posicion_objetivo);
            }
        }
        else
        {
            EnqueueAction(dto.accion, dto.posicion_objetivo);
        }

        // Si no está ejecutando animaciones, procesamos la cola
        if (!_isAnimating)
        {
            StartCoroutine(ProcessQueue());
        }
    }

    private void EnqueueAction(string action, PosDTO target)
    {
        switch (action)
        {
            case "MOVE":
                if (target != null)
                {
                    _actionQueue.Enqueue(AnimateMove(GetWorldPosition(target.x, target.y)));
                }
                break;
            case "BREAK_WALL":
                _actionQueue.Enqueue(AnimateActionShake());
                break;
            case "PICK_UP_VICTIM":
                _actionQueue.Enqueue(AnimatePickUp());
                break;
            case "EXTINGUISH":
                _actionQueue.Enqueue(AnimateAttack());
                break;
        }
    }

    private IEnumerator ProcessQueue()
    {
        _isAnimating = true;
        while (_actionQueue.Count > 0)
        {
            yield return StartCoroutine(_actionQueue.Dequeue());
        }
        _isAnimating = false;
    }

    // ==========================================
    // 1. ANIMACIÓN: MOVIMIENTO FLUIDO
    // ==========================================
    private IEnumerator AnimateMove(Vector3 targetPos)
    {
        // Orientar agente hacia el destino
        Vector3 direction = (targetPos - transform.position).normalized;
        if (direction != Vector3.zero)
        {
            transform.rotation = Quaternion.LookRotation(direction);
        }

        while (Vector3.Distance(transform.position, targetPos) > 0.01f)
        {
            transform.position = Vector3.MoveTowards(transform.position, targetPos, moveSpeed * Time.deltaTime);
            yield return null;
        }
        transform.position = targetPos;
    }

    // ==========================================
    // 2. ANIMACIÓN: ROMPER MURO (Sacudida)
    // ==========================================
    private IEnumerator AnimateActionShake()
    {
        Vector3 originalPos = modelContainer.localPosition;
        float elapsed = 0f;
        float duration = 0.25f;

        while (elapsed < duration)
        {
            float x = Random.Range(-0.1f, 0.1f);
            float z = Random.Range(-0.1f, 0.1f);
            modelContainer.localPosition = originalPos + new Vector3(x, 0, z);
            elapsed += Time.deltaTime;
            yield return null;
        }
        modelContainer.localPosition = originalPos;
    }

    // ==========================================
    // 3. ANIMACIÓN: CARGAR SUPERVIVIENTE (Salto/Crecimiento)
    // ==========================================
    private IEnumerator AnimatePickUp()
    {
        Vector3 originalScale = transform.localScale;
        Vector3 targetScale = originalScale * 1.25f;

        // Estirar
        float elapsed = 0f;
        while (elapsed < 0.15f)
        {
            transform.localScale = Vector3.Lerp(originalScale, targetScale, elapsed / 0.15f);
            elapsed += Time.deltaTime;
            yield return null;
        }

        // Volver a tamaño normal
        elapsed = 0f;
        while (elapsed < 0.15f)
        {
            transform.localScale = Vector3.Lerp(targetScale, originalScale, elapsed / 0.15f);
            elapsed += Time.deltaTime;
            yield return null;
        }
        transform.localScale = originalScale;
    }

    // ==========================================
    // 4. ANIMACIÓN: ATAQUE / ZOMBIE (Giro 360°)
    // ==========================================
    private IEnumerator AnimateAttack()
    {
        float elapsed = 0f;
        float duration = 0.3f;
        Quaternion startRotation = transform.rotation;

        while (elapsed < duration)
        {
            transform.Rotate(Vector3.up, 360f * (Time.deltaTime / duration));
            elapsed += Time.deltaTime;
            yield return null;
        }
        transform.rotation = startRotation;
    }

    private Vector3 GetWorldPosition(int x, int y)
    {
        // Muestra de conversión a coordenadas del Board. Ajusta cellSize si es necesario.
        return new Vector3(x * 1.5f, 0f, y * 1.5f); 
    }
}
