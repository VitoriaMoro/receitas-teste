import streamlit as st
import requests
from functools import lru_cache
import time

# Configuração inicial do app Streamlit
st.set_page_config(
    page_title="ChefAI - Encontre Receitas",
    page_icon="🍳",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Cache para requisições de API (melhora desempenho)
@lru_cache(maxsize=500)
def get_recipe_ids_by_ingredient(ingredient):
    try:
        response = requests.get(
            f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient.strip()}",
            timeout=10
        )
        data = response.json()
        return [meal['idMeal'] for meal in data.get('meals', [])]
    except (requests.exceptions.RequestException, TypeError):
        return []

@lru_cache(maxsize=500)
def get_recipe_details(recipe_id):
    try:
        response = requests.get(
            f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={recipe_id}",
            timeout=10
        )
        return response.json()['meals'][0]
    except (requests.exceptions.RequestException, KeyError, IndexError, TypeError):
        return None

# Função aprimorada para buscar receitas com máximo de correspondências
def get_recipes_by_matching_ingredients(user_ingredients, max_recipes=20):
    user_ingredients_lower = [ing.lower().strip() for ing in user_ingredients]
    unique_ingredients = set(user_ingredients_lower)
    
    # Coleta todos os IDs de receitas possíveis
    all_recipe_ids = set()
    for ingredient in unique_ingredients:
        ids = get_recipe_ids_by_ingredient(ingredient)
        all_recipe_ids.update(ids)
    
    if not all_recipe_ids:
        return []

    # Barra de progresso
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_ids = min(len(all_recipe_ids), 500)
    recipes = []
    processed = 0
    
    # Processa receitas com feedback visual
    for recipe_id in list(all_recipe_ids)[:500]:
        recipe_data = get_recipe_details(recipe_id)
        if not recipe_data:
            continue
            
        # Extrai ingredientes da receita
        recipe_ingredients = []
        for i in range(1, 21):
            ingredient_key = f'strIngredient{i}'
            if recipe_data.get(ingredient_key) and recipe_data[ingredient_key].strip():
                ingredient = recipe_data[ingredient_key].strip().lower()
                recipe_ingredients.append(ingredient)
        
        # Calcula correspondências
        matches = sum(1 for ing in recipe_ingredients if ing in unique_ingredients)
        total_ingredients = len(recipe_ingredients)
        
        # Só inclui receitas com pelo menos 2 correspondências
        if matches >= 2:
            recipes.append({
                'data': recipe_data,
                'ingredients': recipe_ingredients,
                'matches': matches,
                'total': total_ingredients,
                'match_ratio': matches / total_ingredients if total_ingredients > 0 else 0
            })
        
        # Atualiza progresso
        processed += 1
        progress = processed / total_ids
        progress_bar.progress(min(progress, 1.0))
        status_text.text(f"Processando receitas: {processed}/{total_ids} ({int(progress*100)}%)")
        time.sleep(0.01)  # Para não sobrecarregar a API
    
    progress_bar.empty()
    status_text.empty()
    
    if not recipes:
        return []

    # Ordena por: 1. Mais correspondências, 2. Maior proporção, 3. Menos ingredientes faltantes
    recipes.sort(key=lambda x: (
        -x['matches'], 
        -x['match_ratio'], 
        x['total'] - x['matches']
    ))
    
    return recipes[:max_recipes]

# Inicializar session state para armazenar receitas principais
if 'saved_main_recipes' not in st.session_state:
    st.session_state.saved_main_recipes = []

# Interface principal
st.title("🍳 Experiência Cheff - Descubra Novas Receitas Através dos Ingredientes")
st.markdown("Conheça receitas diferentes que combinem com os ingredientes que você tem!")

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
        
        st.success(f"🔍 Encontradas {len(recipes)} receitas com alta compatibilidade!")
        
        # Mostra a receita principal (maior compatibilidade)
        st.subheader("🥇 Receita Principal")
        with st.expander(f"🍳 {main_recipe['data']['strMeal']}", expanded=True):
            st.caption(f"🎯 Compatibilidade: {main_recipe['matches']}/{main_recipe['total']} ingredientes")
            st.progress(main_recipe['match_ratio'])
            
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
        st.subheader("🥈 Outras Ótimas Opções")
        col1, col2 = st.columns(2)
        
        if len(recipes) > 1:
            with col1:
                recipe = recipes[1]
                with st.expander(f"🥈 {recipe['data']['strMeal']}", expanded=True):
                    st.caption(f"🎯 Compatibilidade: {recipe['matches']}/{recipe['total']} ingredientes")
                    st.progress(recipe['match_ratio'])
                    
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
                    st.progress(recipe['match_ratio'])
                    
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

        # Mostrar até 5 receitas adicionais em formato compacto
        if len(recipes) > 3:
            st.subheader("🍽️ Mais Opções Recomendadas")
            cols = st.columns(3)
            for idx, recipe in enumerate(recipes[3:8]):
                with cols[idx % 3]:
                    with st.expander(f"{recipe['data']['strMeal']}"):
                        st.caption(f"🎯 {recipe['matches']}/{recipe['total']} ingredientes")
                        st.image(recipe['data']['strMealThumb'], width=100)
                        if recipe['data'].get('strSource'):
                            st.markdown(f"[Receita]({recipe['data']['strSource']})")
                        if recipe['data'].get('strYoutube'):
                            st.markdown(f"[Vídeo]({recipe['data']['strYoutube']})")

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
st.markdown("Desenvolvido usando [TheMealDB API](https://www.themealdb.com/)")
    
    
