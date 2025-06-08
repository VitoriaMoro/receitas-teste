import streamlit as st
import requests
from googletrans import Translator, LANGCODES

# Configuração do tradutor
translator = Translator()

def translate_ingredients(ingredients, src='pt', dest='en'):
    """Traduz lista de ingredientes para o inglês"""
    translated = []
    for ing in ingredients:
        try:
            # Tentar traduzir com tratamento de erros
            t = translator.translate(ing.strip(), src=src, dest=dest)
            translated.append(t.text.lower())
        except Exception as e:
            # Se falhar, usa o original
            st.warning(f"Erro na tradução de '{ing}': {str(e)}")
            translated.append(ing.strip().lower())
    return translated

def translate_text(text, src='en', dest='pt'):
    """Traduz um texto com tratamento de erros"""
    if not text:
        return text
    
    try:
        # Quebra em partes menores para evitar limite de caracteres
        max_chunk_size = 500
        if len(text) <= max_chunk_size:
            return translator.translate(text, src=src, dest=dest).text
        
        chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
        translated_chunks = []
        for chunk in chunks:
            try:
                t = translator.translate(chunk, src=src, dest=dest)
                translated_chunks.append(t.text)
            except:
                translated_chunks.append(chunk)
        return ' '.join(translated_chunks)
    except Exception as e:
        st.warning(f"Erro na tradução: {str(e)}")
        return text

def translate_recipe_details(recipe, recipe_ingredients, src='en', dest='pt'):
    """Traduz detalhes da receita para português"""
    translated_recipe = recipe.copy()
    
    # Traduz nome da receita
    translated_recipe['strMeal'] = translate_text(recipe.get('strMeal', ''), src, dest)
    
    # Traduz instruções
    translated_recipe['strInstructions'] = translate_text(
        recipe.get('strInstructions', ''), src, dest
    )

    # Traduz lista de ingredientes
    translated_ingredients = [
        translate_text(ing, src, dest).lower() for ing in recipe_ingredients
    ]

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
            st.warning(f"Erro na busca: {str(e)}")
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
            st.warning(f"Erro nos detalhes: {str(e)}")
            continue

    return best_recipe, best_matched_ingredients, original_ingredients, max_matches

# Interface do Streamlit
st.set_page_config(
    page_title="Chef Virtual",
    page_icon="🍳",
    layout="centered",
    initial_sidebar_state="expanded"
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
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .stTextArea > div > div > textarea {
        min-height: 200px;
    }
    footer {
        visibility: hidden;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.title("🍳 Chef Virtual - Encontre Receitas com Seus Ingredientes")
st.markdown("Digite os ingredientes disponíveis e encontramos a receita mais compatível para você!")

# Entrada de ingredientes
user_input = st.text_input("Ingredientes (separados por vírgula):", 
                          placeholder="Ex: arroz, frango, tomate, cebola...",
                          help="Digite os ingredientes que você tem disponível, separados por vírgulas")

user_ingredients = [ing.strip() for ing in user_input.split(',') if ing.strip()]

# Botão de busca
if st.button("Buscar Receitas 🔍", use_container_width=True):
    if not user_ingredients:
        st.warning("Por favor, insira pelo menos um ingrediente válido!")
    else:
        with st.spinner("Procurando receitas compatíveis..."):
            recipe, matched_ingredients, original_ingredients, compatibility_score = get_recipe_with_max_matching_ingredients(user_ingredients)
        
        if not recipe:
            st.error("Nenhuma receita encontrada com esses ingredientes. Tente outros ingredientes!")
        else:
            # Traduz detalhes da receita
            with st.spinner("Traduzindo receita para português..."):
                translated_recipe, translated_ingredients = translate_recipe_details(
                    recipe, matched_ingredients
                )
            
            # Extrai links
            youtube = recipe.get('strYoutube', '')
            source = recipe.get('strSource', '')
            
            # Exibe resultados
            st.success("Receita encontrada com sucesso!")
            st.markdown(f"<h2 class='header'>🏆 {translated_recipe.get('strMeal', recipe['strMeal'])}</h2>", 
                        unsafe_allow_html=True)
            
            # Cálculo do percentual de compatibilidade
            if len(user_ingredients) > 0:
                match_percent = min(100, int((compatibility_score / len(user_ingredients)) * 100)
            else:
                match_percent = 0
            
            # Barra de compatibilidade
            st.subheader(f"Compatibilidade: {match_percent}%")
            st.progress(match_percent / 100)
            
            # Links
            if youtube or source:
                st.subheader("🔗 Links Úteis")
                cols = st.columns(2)
                if source:
                    cols[0].markdown(f"[Fonte Original]({source})")
                if youtube:
                    cols[1].markdown(f"[Vídeo no YouTube]({youtube})")
            
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
                
                st.markdown(f"<span class='{color_class}'>{icon} {ing.capitalize()}</span>", 
                            unsafe_allow_html=True)
            
            # Instruções
            st.subheader("📝 Instruções de Preparo:")
            instructions = translated_recipe.get('strInstructions', 'Instruções não disponíveis.')
            st.text_area("", value=instructions, height=300, label_visibility="collapsed")
            
            # Créditos
            st.caption("Dados fornecidos por TheMealDB.com • Traduções por Google Translate")

# Rodapé
st.markdown("---")
st.markdown("Desenvolvido com ❤️ usando Python, Streamlit e TheMealDB API")

# Sidebar com informações adicionais
with st.sidebar:
    st.header("Sobre o Chef Virtual")
    
    
    
