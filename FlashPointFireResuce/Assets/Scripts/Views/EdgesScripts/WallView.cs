using UnityEngine;

public class WallView : EdgeView
{
    public override void UpdateState(EdgeDTO dto)
    {
        if (dto.hp >= 2)
        {
            // Muro intacto
            gameObject.SetActive(true);
            transform.localScale = Vector3.one;
        }
        else if (dto.hp == 1)
        {
            // Truco ArtTech: Aplastamos el muro en Y y Z para simular que está parcialmente derrumbado
            gameObject.SetActive(true);
            transform.localScale = new Vector3(1f, 0.4f, 0.8f);
        }
        else
        {
            // Muro colapsado
            gameObject.SetActive(false);
        }
    }
}