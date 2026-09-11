using UnityEngine;

public class DoorView : EdgeView
{
    public override void UpdateState(EdgeDTO dto)
    {
        if (dto.cerrado)
        {
            gameObject.SetActive(true);
            // Aseguramos que bloquee el paso visualmente
            transform.localScale = Vector3.one; 
        }
        else
        {
            // Truco ArtTech: En lugar de hacerla desaparecer, la achatamos drásticamente en el eje X/Z 
            // simulando que la puerta fue reventada y quedó pegada a un lado del marco.
            gameObject.SetActive(true);
            transform.localScale = new Vector3(0.1f, 1f, 1f); 
        }
    }
}