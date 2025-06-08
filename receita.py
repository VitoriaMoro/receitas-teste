import streamlit as st
import requests
from translate import Translator

# Configuração do tradutor
translator_pt_to_en = Translator(from_lang="pt", to_lang="en")
translator_en_to_pt = Translator(from_lang="en", to_lang="pt")

def translate_ingredients(ingredients, src='pt', dest='en'):
    """Traduz lista de ingredientes para o inglês"""
    translated = []
    for ing in ingredients:
        try:
            if src == 'pt' and dest == 'en':
                t = translator_pt_to_en.translate(ing.strip())
            else:
                t = translator_en_to_pt.translate(ing.strip())
            translated.append(t.lower())
        except Exception as e:
            st.warning(f"Erro na tradução: {e}")
            translated.append(ing.strip().lower())
    return translated

def translate_recipe_details(recipe, recipe_ingredients, src='en', dest='pt'):
    """Traduz detalhes da receita para português"""
    translated_recipe = recipe.copy()
    
    # Traduz nome da receita
    try:
        if src == 'en' and dest == 'pt':
            translated_recipe['strMeal'] = translator_en_to_pt.translate(recipe['strMeal'])
    except:
        pass

    # Traduz instruções em chunks
    try:
        instructions = recipe['strInstructions']
        chunks = [instructions[i:i+500] for i in range(0, len(instructions), 500)]
        translated_chunks = []
        for chunk in chunks:
            try:
                if src == 'en' and dest == 'pt':
                    t = translator_en_to_pt.translate(chunk)
                    translated_chunks.append(t)
            except:
                translated_chunks.append(chunk)
        translated_recipe['strInstructions'] = ' '.join(translated_chunks)
    except:
        pass

    # Traduz lista de ingredientes
    translated_ingredients = []
    for ing in recipe_ingredients:
        try:
            if src == 'en' and dest == 'pt':
                t = translator_en_to_pt.translate(ing)
                translated_ingredients.append(t.lower())
        except:
            translated_ingredients.append(ing)

    return translated_recipe, translated_ingredients

def get_recipe_with_max_matching_ingredients(user_ingredients):
    """Busca a receita com maior compatibilidade de ingredientes"""
    translated_ingredients = translate_ingredients(user_ingredients)
    
    # Busca IDs de receitas
    recipe_ids = set()
    for ingredient in translated_ingredients:
        try:
            response = requests.get(
                f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient}",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('meals'):
                    for meal in data['meals']:
                        recipe_ids.add(meal['idMeal'])
        except Exception as e:
            st.warning(f"Erro na busca: {e}")
            continue

    if not recipe_ids:
        return None, [], [], 0

    # Busca detalhes das receitas
    best_recipe = None
    max_matches = 0
    best_matched_ingredients = []
    original_ingredients = []

    for recipe_id in recipe_ids:
        try:
            response = requests.get(
                f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={recipe_id}",
                timeout=10
            )
            if response.status_code == 200:
                recipe_data = response.json().get('meals', [])
                if recipe_data:
                    recipe_data = recipe_data[0]
                    
                    # Extrai ingredientes
                    recipe_ingredients = []
                    for i in range(1, 21):
                        ingredient = recipe_data.get(f'strIngredient{i}', '')
                        if ingredient and ingredient.strip():
                            recipe_ingredients.append(ingredient.strip().lower())
                    
                    # Calcula correspondências
                    matches = sum(1 for ing in recipe_ingredients if ing in translated_ingredients)
                    
                    if matches > max_matches:
                        max_matches = matches
                        best_recipe = recipe_data
                        best_matched_ingredients = recipe_ingredients
                        original_ingredients = recipe_ingredients.copy()
        except Exception as e:
            st.warning(f"Erro nos detalhes: {e}")
            continue

    return best_recipe, best_matched_ingredients, original_ingredients, max_matches

# Interface do Streamlit
st.set_page_config(
    page_title="Chef Virtual",
    page_icon="🍳",
    layout="centered"
)

# CSS personalizado
st.markdown("""
<style>
    .header {
        color: #FF4B4B;
        border-bottom: 2px solid #FF4B4B;
        padding-bottom: 10px;
    }
    .ingredient-match {
        color: #00C853;
        font-weight: bold;
    }
    .ingredient-miss {
        color: #FF5252;
    }
    .compatibility {
        font-size: 1.2em;
        background-color: #E3F2FD;
        padding: 10px;
        border-radius: 5px;
        margin: 15px 0;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.title("🍳 Chef Virtual - Encontre Receitas com Seus Ingredientes")
st.markdown("Digite os ingredientes que você tem disponível e encontraremos a receita mais compatível!")

# Entrada de ingredientes
user_input = st.text_input("Ingredientes (separados por vírgula):", placeholder="Ex: arroz, frango, tomate, cebola...")
user_ingredients = [ing.strip() for ing in user_input.split(',') if ing.strip()]

if st.button("Buscar Receitas 🔍"):
    if not user_ingredients:
        st.warning("Por favor, insira pelo menos um ingrediente válido!")
    else:
        with st.spinner("Procurando receitas compatíveis..."):
            recipe, matched_ingredients, original_ingredients, compatibility_score = get_recipe_with_max_matching_ingredients(user_ingredients)
        
        if not recipe:
            st.error("Nenhuma receita encontrada com esses ingredientes. Tente outros ingredientes!")
        else:
            # Traduz detalhes da receita
            translated_recipe, translated_ingredients = translate_recipe_details(
                recipe, matched_ingredients
            )
            
            # Extrai links
            youtube = recipe.get('strYoutube', '')
            source = recipe.get('strSource', '')
            
            # Exibe resultados
            st.success("Receita encontrada com sucesso!")
            st.markdown(f"<h2 class='header'>🏆 {translated_recipe.get('strMeal', recipe['strMeal'])}</h2>", unsafe_allow_html=True)
            
            # Cálculo do percentual de compatibilidade
            if len(user_ingredients) > 0:
                match_percent = min(100, int((compatibility_score / len(user_ingredients)) * 100))
            else:
                match_percent = 0
            
            # Barra de compatibilidade
            st.subheader(f"Compatibilidade: {match_percent}%")
            st.progress(match_percent / 100)
            
            # Links
            col1, col2 = st.columns(2)
            if source:
                col1.markdown(f"🔗 [Fonte Original]({source})")
            if youtube:
                col2.markdown(f"📺 [Vídeo no YouTube]({youtube})")
            
            # Ingredientes com marcação
            st.subheader("🍽️ Ingredientes:")
            user_ingredients_en = translate_ingredients(user_ingredients)
            for i, ing in enumerate(translated_ingredients):
                if i < len(original_ingredients):
                    has_ingredient = original_ingredients[i] in user_ingredients_en
                else:
                    has_ingredient = False
                icon = "✓" if has_ingredient else "✗"
                color_class = "ingredient-match" if has_ingredient else "ingredient-miss"
                st.markdown(f"<span class='{color_class}'>{icon} {ing.capitalize()}</span>", unsafe_allow_html=True)
            
            # Instruções
            st.subheader("📝 Instruções:")
            instructions = translated_recipe.get('strInstructions', recipe.get('strInstructions', 'Instruções não disponíveis.'))
            st.text_area("", value=instructions, height=300)
            
            # Créditos
            st.caption("Dados fornecidos por TheMealDB.com")

# Rodapé
st.markdown("---")
st.markdown("Desenvolvido com ❤️ usando Python, Streamlit e TheMealDB API")
           
