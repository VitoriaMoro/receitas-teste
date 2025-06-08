import streamlit as st
import requests
from googletrans import Translator

# Configuração do tradutor
translator = Translator()

st.set_page_config(
    page_title="ChefAI - Encontre Receitas",
    page_icon="🍳",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Função para traduzir texto
def translate_text(text, src='pt', dest='en'):
    try:
        if not text.strip():
            return text
        translation = translator.translate(text, src=src, dest=dest)
        return translation.text
    except Exception as e:
        st.error(f"Erro na tradução: {e}")
        return text

# Função para traduzir lista de ingredientes
def translate_ingredients(ingredients, src='pt', dest='en'):
    translated = []
    for ing in ingredients:
        translated.append(translate_text(ing.strip(), src, dest).lower())
    return translated

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
    
    for recipe_id in list(recipe_ids)[:200]:  # Limita a 200 buscas para performance
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

# Função para traduzir uma receita completa
def translate_recipe(recipe):
    # Traduz campos principais
    translated_data = {
        'strMeal': translate_text(recipe['data']['strMeal'], src='en', dest='pt'),
        'strInstructions': translate_text(recipe['data']['strInstructions'], src='en', dest='pt'),
        'strCategory': translate_text(recipe['data'].get('strCategory', ''), src='en', dest='pt'),
        'strArea': translate_text(recipe['data'].get('strArea', ''), src='en', dest='pt'),
    }
    
    # Mantém campos originais que não precisam de tradução
    for key in ['strSource', 'strYoutube', 'idMeal']:
        if key in recipe['data']:
            translated_data[key] = recipe['data'][key]
    
    # Traduz lista de ingredientes
    translated_ingredients = [
        translate_text(ing, src='en', dest='pt').capitalize()
        for ing in recipe['ingredients']
    ]
    
    return {
        'data': translated_data,
        'ingredients': translated_ingredients,
        'matches': recipe['matches'],
        'total': recipe['total']
    }

# Inicializar session state para armazenar receitas principais
if 'saved_main_recipes' not in st.session_state:
    st.session_state.saved_main_recipes = []

st.title("🍳 Experiência Chef - Descubra Novas Receitas Através dos Ingredientes")
st.markdown("Conheça receitas diferentes que combinem com os ingredientes que você tem!")

user_input = st.text_input(
    "Digite seus ingredientes (separados por vírgula):",
    placeholder="Ex: ovo, farinha, açúcar",
    key="ingredient_input"
)

# Barra lateral 
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
    
    # Traduz ingredientes para inglês
    user_ingredients_pt = [ing.strip() for ing in user_input.split(',') if ing.strip()]
    user_ingredients_en = translate_ingredients(user_ingredients_pt, src='pt', dest='en')
    
    st.info(f"Ingredientes traduzidos para busca: {', '.join(user_ingredients_en)}")
    
    with st.spinner("Procurando receitas incríveis para você..."):
        recipes_en = get_recipes_by_matching_ingredients(user_ingredients_en)
    
    if not recipes_en:
        st.error("Nenhuma receita encontrada com esses ingredientes. Tente outros ingredientes!")
    else:
        # Traduz receitas para português
        recipes_pt = [translate_recipe(recipe) for recipe in recipes_en[:3]]  # Traduz apenas as 3 primeiras para performance
        
        # Salva apenas a receita principal na session state
        main_recipe = recipes_pt[0]
        if main_recipe not in st.session_state.saved_main_recipes:
            st.session_state.saved_main_recipes.insert(0, main_recipe)
        
        # Mantém apenas as últimas 10 receitas principais
        st.session_state.saved_main_recipes = st.session_state.saved_main_recipes[:10]
        
        st.success(f"🔍 Encontradas {len(recipes_en)} receitas!")
        
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
                match_indicator = "✅" if translate_text(ing, src='pt', dest='en').lower() in user_ingredients_en else "❌"
                st.markdown(f"{match_indicator} {ing}")
            
            st.subheader("👩‍🍳 Instruções:")
            st.write(main_recipe['data']['strInstructions'])
            
            st.caption(f"🗂️ Categoria: {main_recipe['data'].get('strCategory', 'N/A')}")
            st.caption(f"🌍 Cozinha: {main_recipe['data'].get('strArea', 'N/A')}")
        
        # Mostra mais duas opções de receitas com ingredientes e instruções
        if len(recipes_pt) > 1:
            st.subheader("🥈 Outras Opções")
            col1, col2 = st.columns(2)
            
            with col1:
                recipe = recipes_pt[1]
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
                        match_indicator = "✅" if translate_text(ing, src='pt', dest='en').lower() in user_ingredients_en else "❌"
                        st.markdown(f"{match_indicator} {ing}")
                    
                    # Instruções
                    st.subheader("👩‍🍳 Instruções:")
                    st.write(recipe['data']['strInstructions'])
                    
                    # Metadados
                    st.caption(f"🗂️ Categoria: {recipe['data'].get('strCategory', 'N/A')}")
                    st.caption(f"🌍 Cozinha: {recipe['data'].get('strArea', 'N/A')}")
            
            if len(recipes_pt) > 2:
                with col2:
                    recipe = recipes_pt[2]
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
                            match_indicator = "✅" if translate_text(ing, src='pt', dest='en').lower() in user_ingredients_en else "❌"
                            st.markdown(f"{match_indicator} {ing}")
                        
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
        st.markdown(f"• {ing}")
    
    st.subheader("👩‍🍳 Instruções:")
    st.write(recipe['data']['strInstructions'])
    
    st.caption(f"🗂️ Categoria: {recipe['data'].get('strCategory', 'N/A')}")
    st.caption(f"🌍 Cozinha: {recipe['data'].get('strArea', 'N/A')}")
    
    # Botão para voltar
    if st.button("Voltar para os resultados"):
        del st.session_state.selected_recipe

st.markdown("---")
st.markdown("Desenvolvido usando [TheMealDB API](https://www.themealdb.com/)")
