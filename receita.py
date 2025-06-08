
import streamlit as st
import requests
from googletrans import Translator

def translate_ingredients(ingredients, src='pt', dest='en'):
    """Traduz lista de ingredientes para o inglês usando googletrans"""
    translator = Translator()
    translated = []
    for ing in ingredients:
        try:
            t = translator.translate(ing.strip(), src=src, dest=dest)
            translated.append(t.text.lower())
        except:
            # Fallback: usa o original se falhar a tradução
            translated.append(ing.strip().lower())
    return translated

def translate_recipe_details(recipe, recipe_ingredients, src='en', dest='pt'):
    """Traduz detalhes da receita para português"""
    translator = Translator()
    translated_recipe = recipe.copy()

    # Traduz nome da receita
    try:
        translated_recipe['strMeal'] = translator.translate(
            recipe['strMeal'], src=src, dest=dest
        ).text
    except:
        pass

    # Traduz instruções
    try:
        instructions = recipe['strInstructions']
        # Quebra em partes menores para evitar limite de caracteres
        chunks = [instructions[i:i+500] for i in range(0, len(instructions), 500)]
        translated_chunks = []
        for chunk in chunks:
            try:
                t = translator.translate(chunk, src=src, dest=dest)
                translated_chunks.append(t.text)
            except:
                translated_chunks.append(chunk)
        translated_recipe['strInstructions'] = ' '.join(translated_chunks)
    except:
        pass

    # Traduz lista de ingredientes
    translated_ingredients = []
    for ing in recipe_ingredients:
        try:
            t = translator.translate(ing, src=src, dest=dest)
            translated_ingredients.append(t.text.lower())
        except:
            translated_ingredients.append(ing)

    return translated_recipe, translated_ingredients

def get_recipe_with_max_matching_ingredients(user_ingredients):
    # Passo 1: Traduzir ingredientes para inglês
    translated_ingredients = translate_ingredients(user_ingredients)

    # Passo 2: Buscar IDs de receitas
    recipe_ids = set()
    for ingredient in translated_ingredients:
        try:
            response = requests.get(
                f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient}",
                timeout=5
            )
            data = response.json()
            if data.get('meals'):
                for meal in data['meals']:
                    recipe_ids.add(meal['idMeal'])
        except requests.exceptions.RequestException:
            continue

    if not recipe_ids:
        return None, [], [], 0 # Adiciona 0 para a pontuação

    # Passo 3: Buscar detalhes e encontrar melhor correspondência
    best_recipe = None
    max_matches = 0
    best_matched_ingredients = []
    original_ingredients = []

    for recipe_id in recipe_ids:
        try:
            response = requests.get(
                f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={recipe_id}",
                timeout=5
            )
            recipe_data = response.json()['meals'][0]

            # Extrair ingredientes da receita
            recipe_ingredients = []
            for i in range(1, 21):
                ingredient_value = recipe_data.get(f'strIngredient{i}')
                # Check if the ingredient_value is not None before processing
                if ingredient_value and ingredient_value.strip():
                     ingredient = ingredient_value.strip().lower()
                     recipe_ingredients.append(ingredient)


            # Contar correspondências
            matches = sum(1 for ing in recipe_ingredients if ing in translated_ingredients)

            if matches > max_matches:
                max_matches = matches
                best_recipe = recipe_data
                best_matched_ingredients = recipe_ingredients
                original_ingredients = recipe_ingredients.copy()

        except (requests.exceptions.RequestException, KeyError, IndexError):
            continue

    return best_recipe, best_matched_ingredients, original_ingredients, max_matches # Retorna a pontuação

if __name__ == "__main__":
    # Obter ingredientes do usuário
    user_input = input("Digite os ingredientes separados por vírgula: ")
    user_ingredients = [ing.strip() for ing in user_input.split(',') if ing.strip()]

    if not user_ingredients:
        print("Nenhum ingrediente válido fornecido!")
    else:
        recipe, matched_ingredients, original_ingredients, compatibility_score = get_recipe_with_max_matching_ingredients(user_ingredients) # Captura a pontuação

        if not recipe:
            print("Nenhuma receita encontrada com esses ingredientes.")
        else:
            # Traduzir detalhes da receita para português
            translated_recipe, translated_ingredients = translate_recipe_details(
                recipe, matched_ingredients
            )

            # Extrair links
            youtube = recipe.get('strYoutube', '')
            source = recipe.get('strSource', '')


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
            st.markdown(f"<h2 class='header'>🏆 {translated_recipe['strMeal']}</h2>", unsafe_allow_html=True)
            
            # Barra de compatibilidade
            match_percent = min(100, int(compatibility_score / len(user_ingredients) * 100)
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
                has_ingredient = original_ingredients[i] in user_ingredients_en if i < len(original_ingredients) else False
                icon = "✓" if has_ingredient else "✗"
                color_class = "ingredient-match" if has_ingredient else "ingredient-miss"
                st.markdown(f"<span class='{color_class}'>{icon} {ing.capitalize()}</span>", unsafe_allow_html=True)
            
            # Instruções
            st.subheader("📝 Instruções:")
            instructions = translated_recipe['strInstructions']
            st.text_area("", value=instructions, height=300)
            
            # Créditos
            st.caption("Dados fornecidos por TheMealDB.com")

# Rodapé
st.markdown("---"
st.markdown("Desenvolvido com ❤️ usando Python, Streamlit e TheMealDB API")

