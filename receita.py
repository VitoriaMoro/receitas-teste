import streamlit as st
import requests

# Configuração inicial do app Streamlit
st.set_page_config(
    page_title="ChefAI - Encontre Receitas",
    page_icon="🍳",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Função para buscar receitas
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

# Inicializar session state para armazenar receitas principais
if 'saved_main_recipes' not in st.session_state:
    st.session_state.saved_main_recipes = []

# Interface principal
st.title("🍳 ChefAI - Encontre Receitas por Ingredientes")
st.markdown("Descubra receitas que combinam com os ingredientes que você tem!")

user_input = st.text_input(
    "Digite seus ingredientes (separados por vírgula):",
    placeholder="Ex: ovo, farinha, açúcar",
    key="ingredient_input"
)

# Barra lateral para receitas principais salvas
with st.sidebar:
    st.header("📚 Receitas Principais Salvas")
    st.caption("Suas últimas receitas principais pesquisadas")
    
    if not st.session_state.saved_main_recipes:
        st.info("Nenhuma receita salva ainda. Faça uma busca para começar!")
    else:
        for i, recipe in enumerate(st.session_state.saved_main_recipes):
            with st.expander(f"{i+1}. {recipe['data']['strMeal']}"):
                st.caption(f"Compatibilidade: {recipe['matches']}/{recipe['total']}")
                st.caption(f"🗂️ {recipe['data'].get('strCategory', 'N/A')}")
                
                if st.button("Ver Receita Completa", key=f"view_{i}"):
                    st.session_state.selected_recipe = recipe
                
                if st.button("Remover", key=f"remove_{i}"):
                    st.session_state.saved_main_recipes.pop(i)
                    st.experimental_rerun()

# Botão de busca
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
        # Salva apenas a receita principal na session state
        main_recipe = recipes[0]
        if main_recipe not in st.session_state.saved_main_recipes:
            st.session_state.saved_main_recipes.insert(0, main_recipe)
        
        # Mantém apenas as últimas 10 receitas principais
        st.session_state.saved_main_recipes = st.session_state.saved_main_recipes[:10]
        
        st.success(f"🔍 Encontradas {len(recipes)} receitas!")
        
        # Mostra a receita principal (maior compatibilidade)
        st.subheader("🥇 Receita Principal")
        with st.expander(f"🍳 {main_recipe['data']['strMeal']}", expanded=True):
            st.caption(f"🎯 Compatibilidade: {main_recipe['matches']}/{main_recipe['total']} ingredientes")
            st.progress(main_recipe['matches'] / main_recipe['total'])
            
            col1, col2 = st.columns(2)
            if main_recipe['data'].get('strSource'):
                col1.markdown(f"🔗 [Receita Original]({main_recipe['data']['strSource']})")
            if main_recipe['data'].get('strYoutube'):
                col2.markdown(f"📺 [Vídeo no YouTube]({main_recipe['data']['strYoutube']})")
            
            st.subheader("📋 Ingredientes:")
            for ing in main_recipe['ingredients']:
                match_indicator = "✅" if ing in [i.lower() for i in user_ingredients] else "❌"
                st.markdown(f"{match_indicator} {ing.capitalize()}")
            
            st.subheader("👩‍🍳 Instruções:")
            st.write(main_recipe['data']['strInstructions'])
            
            st.caption(f"🗂️ Categoria: {main_recipe['data'].get('strCategory', 'N/A')}")
            st.caption(f"🌍 Cozinha: {main_recipe['data'].get('strArea', 'N/A')}")
        
        # Mostra mais duas opções de receitas com ingredientes e instruções
        st.subheader("🥈 Outras Opções")
        col1, col2 = st.columns(2)
        
        if len(recipes) > 1:
            with col1:
                recipe = recipes[1]
                with st.expander(f"🥈 {recipe['data']['strMeal']}", expanded=True):
                    st.caption(f"🎯 Compatibilidade: {recipe['matches']}/{recipe['total']} ingredientes")
                    st.progress(recipe['matches'] / recipe['total'])
                    
                    # Links
                    link_col1, link_col2 = st.columns(2)
                    if recipe['data'].get('strSource'):
                        link_col1.markdown(f"🔗 [Receita Original]({recipe['data']['strSource']})")
                    if recipe['data'].get('strYoutube'):
                        link_col2.markdown(f"📺 [Vídeo no YouTube]({recipe['data']['strYoutube']})")
                    
                    # Ingredientes
                    st.subheader("📋 Ingredientes:")
                    for ing in recipe['ingredients']:
                        match_indicator = "✅" if ing in [i.lower() for i in user_ingredients] else "❌"
                        st.markdown(f"{match_indicator} {ing.capitalize()}")
                    
                    # Instruções
                    st.subheader("👩‍🍳 Instruções:")
                    st.write(recipe['data']['strInstructions'])
                    
                    # Metadados
                    st.caption(f"🗂️ Categoria: {recipe['data'].get('strCategory', 'N/A')}")
                    st.caption(f"🌍 Cozinha: {recipe['data'].get('strArea', 'N/A')}")
        
        if len(recipes) > 2:
            with col2:
                recipe = recipes[2]
                with st.expander(f"🥉 {recipe['data']['strMeal']}", expanded=True):
                    st.caption(f"🎯 Compatibilidade: {recipe['matches']}/{recipe['total']} ingredientes")
                    st.progress(recipe['matches'] / recipe['total'])
                    
                    # Links
                    link_col1, link_col2 = st.columns(2)
                    if recipe['data'].get('strSource'):
                        link_col1.markdown(f"🔗 [Receita Original]({recipe['data']['strSource']})")
                    if recipe['data'].get('strYoutube'):
                        link_col2.markdown(f"📺 [Vídeo no YouTube]({recipe['data']['strYoutube']})")
                    
                    # Ingredientes
                    st.subheader("📋 Ingredientes:")
                    for ing in recipe['ingredients']:
                        match_indicator = "✅" if ing in [i.lower() for i in user_ingredients] else "❌"
                        st.markdown(f"{match_indicator} {ing.capitalize()}")
                    
                    # Instruções
                    st.subheader("👩‍🍳 Instruções:")
                    st.write(recipe['data']['strInstructions'])
                    
                    # Metadados
                    st.caption(f"🗂️ Categoria: {recipe['data'].get('strCategory', 'N/A')}")
                    st.caption(f"🌍 Cozinha: {recipe['data'].get('strArea', 'N/A')}")

# Mostrar receita selecionada da barra lateral
if 'selected_recipe' in st.session_state:
    st.subheader("📖 Receita Selecionada")
    recipe = st.session_state.selected_recipe
    
    st.subheader(f"🍳 {recipe['data']['strMeal']}")
    st.caption(f"🎯 Compatibilidade: {recipe['matches']}/{recipe['total']} ingredientes")
    st.progress(recipe['matches'] / recipe['total'])
    
    col1, col2 = st.columns(2)
    if recipe['data'].get('strSource'):
        col1.markdown(f"🔗 [Receita Original]({recipe['data']['strSource']})")
    if recipe['data'].get('strYoutube'):
        col2.markdown(f"📺 [Vídeo no YouTube]({recipe['data']['strYoutube']})")
    
    st.subheader("📋 Ingredientes:")
    for ing in recipe['ingredients']:
        # Como não temos a lista original do usuário, mostramos sem indicadores
        st.markdown(f"• {ing.capitalize()}")
    
    st.subheader("👩‍🍳 Instruções:")
    st.write(recipe['data']['strInstructions'])
    
    st.caption(f"🗂️ Categoria: {recipe['data'].get('strCategory', 'N/A')}")
    st.caption(f"🌍 Cozinha: {recipe['data'].get('strArea', 'N/A')}")
    
    # Botão para voltar
    if st.button("Voltar para os resultados"):
        del st.session_state.selected_recipe

# Rodapé
st.markdown("---")
st.markdown("Desenvolvido com ❤️ usando [TheMealDB API](https://www.themealdb.com/)")
    
    
