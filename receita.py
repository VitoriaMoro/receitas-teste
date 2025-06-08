import streamlit as st
import requests

def get_recipe_with_max_matching_ingredients(user_ingredients):
    recipe_ids = set()
    user_ingredients_lower = [ing.lower() for ing in user_ingredients]
    
    for ingredient in user_ingredients_lower:
        try:
            response = requests.get(
                f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient.strip()}"
            )
            data = response.json()
            if data.get('meals'):
                for meal in data['meals']:
                    recipe_ids.add(meal['idMeal'])
        except (requests.exceptions.RequestException, TypeError):
            continue

    if not recipe_ids:
        return None, [], 0, 0

    best_recipe = None
    max_matches = 0
    best_matched_ingredients = []
    
    for recipe_id in recipe_ids:
        try:
            response = requests.get(
                f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={recipe_id}"
            )
            recipe_data = response.json()['meals'][0]
            
            recipe_ingredients = []
            for i in range(1, 21):
                ingredient_key = f'strIngredient{i}'
                if recipe_data.get(ingredient_key) and recipe_data[ingredient_key].strip():
                    ingredient = recipe_data[ingredient_key].strip().lower()
                    recipe_ingredients.append(ingredient)
            
            matches = sum(1 for ing in recipe_ingredients if ing in user_ingredients_lower)
            
            if matches > max_matches or (matches == max_matches and not best_recipe):
                max_matches = matches
                best_recipe = recipe_data
                best_matched_ingredients = recipe_ingredients
        
        except (requests.exceptions.RequestException, KeyError, IndexError, TypeError):
            continue

    total_ingredients = len(best_matched_ingredients) if best_recipe else 0
    return best_recipe, best_matched_ingredients, max_matches, total_ingredients

# Configuração do app Streamlit
st.set_page_config(page_title="Encontre Receitas", page_icon="🍳", layout="centered")

st.title("🍳 ChefAI - Encontre Receitas por Ingredientes")
st.markdown("Descubra receitas que combinam com os ingredientes que você tem!")

user_input = st.text_input(
    "Digite seus ingredientes (separados por vírgula):",
    placeholder="Ex: ovo, farinha, açúcar"
)

if st.button("Buscar Receitas") or user_input:
    if not user_input:
        st.warning("Por favor, digite pelo menos um ingrediente!")
        st.stop()
    
    user_ingredients = [ing.strip() for ing in user_input.split(',') if ing.strip()]
    
    with st.spinner("Procurando receitas incríveis para você..."):
        recipe, recipe_ingredients, matches, total_ingredients = get_recipe_with_max_matching_ingredients(user_ingredients)
    
    if not recipe:
        st.error("Nenhuma receita encontrada com esses ingredientes. Tente outros ingredientes!")
    else:
        # Mostrar estatísticas de compatibilidade
        st.success(f"🎯 **Compatibilidade:** {matches}/{total_ingredients} ingredientes")
        st.progress(matches / total_ingredients if total_ingredients > 0 else 0)
        
        # Card da receita
        st.subheader(f"🏆 {recipe['strMeal']}")
        
        col1, col2 = st.columns(2)
        if recipe.get('strSource'):
            col1.markdown(f"🔗 [Receita Original]({recipe['strSource']})")
        if recipe.get('strYoutube'):
            col2.markdown(f"📺 [Vídeo no YouTube]({recipe['strYoutube']})")
        
        # Ingredientes com indicadores
        st.subheader("🍽️ Ingredientes:")
        for ing in recipe_ingredients:
            match_indicator = "✅" if ing in [i.lower() for i in user_ingredients] else "❌"
            st.markdown(f"{match_indicator} {ing.capitalize()}")
        
        # Instruções
        st.subheader("📝 Instruções:")
        st.write(recipe['strInstructions'])
        
        # Categoria e área
        if recipe.get('strCategory') or recipe.get('strArea'):
            st.caption(f"🗂️ Categoria: {recipe.get('strCategory', 'N/A')} | 🌍 Cozinha: {recipe.get('strArea', 'N/A')}")

# Rodapé
st.markdown("---")
st.markdown("Desenvolvido com ❤️ usando [TheMealDB API](https://www.themealdb.com/)")

# Para rodar localmente (descomente se necessário)
# if __name__ == "__main__":
#     import os
#     os.system("streamlit run app.py")
    
    
    
