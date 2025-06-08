import streamlit as st
import requests

def get_recipes_by_matching_ingredients(user_ingredients, max_recipes=10):
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
        return []

    recipes = []
    
    for recipe_id in list(recipe_ids)[:50]:  # Limita a 50 buscas para performance
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
            total_ingredients = len(recipe_ingredients)
            
            recipes.append({
                'data': recipe_data,
                'ingredients': recipe_ingredients,
                'matches': matches,
                'total': total_ingredients
            })
        
        except (requests.exceptions.RequestException, KeyError, IndexError, TypeError):
            continue

    # Ordena receitas por correspondência (maior primeiro)
    recipes.sort(key=lambda x: x['matches'], reverse=True)
    return recipes[:max_recipes]  # Retorna no máximo N receitas

# Configuração do app Streamlit
st.set_page_config(
    page_title="Encontre Receitas",
    page_icon="🍳",
    layout="centered",
    initial_sidebar_state="expanded"
)

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
        recipes = get_recipes_by_matching_ingredients(user_ingredients)
    
    if not recipes:
        st.error("Nenhuma receita encontrada com esses ingredientes. Tente outros ingredientes!")
    else:
        st.success(f"🔍 Encontradas {len(recipes)} receitas!")
        
        # Cria abas para cada receita
        tabs = st.tabs([f"Receita #{i+1}" for i in range(len(recipes))])
        
        for idx, tab in enumerate(tabs):
            recipe = recipes[idx]
            with tab:
                # Cabeçalho com informações básicas
                st.subheader(f"🍳 {recipe['data']['strMeal']}")
                st.caption(f"🎯 Compatibilidade: {recipe['matches']}/{recipe['total']} ingredientes")
                st.progress(recipe['matches'] / recipe['total'])
                
                # Colunas para links
                col1, col2 = st.columns(2)
                if recipe['data'].get('strSource'):
                    col1.markdown(f"🔗 [Receita Original]({recipe['data']['strSource']})")
                if recipe['data'].get('strYoutube'):
                    col2.markdown(f"📺 [Vídeo no YouTube]({recipe['data']['strYoutube']})")
                
                # Ingredientes com indicadores
                st.subheader("📋 Ingredientes:")
                for ing in recipe['ingredients']:
                    match_indicator = "✅" if ing in [i.lower() for i in user_ingredients] else "❌"
                    st.markdown(f"{match_indicator} {ing.capitalize()}")
                
                # Instruções de preparo
                st.subheader("👩‍🍳 Instruções:")
                st.write(recipe['data']['strInstructions'])
                
                # Metadados
                st.caption(f"🗂️ Categoria: {recipe['data'].get('strCategory', 'N/A')}")
                st.caption(f"🌍 Cozinha: {recipe['data'].get('strArea', 'N/A')}")

# Rodapé
st.markdown("---")
st.markdown("Desenvolvido com ❤️ usando [TheMealDB API](https://www.themealdb.com/)")
    
    
    
