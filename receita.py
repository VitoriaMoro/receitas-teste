import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from tqdm import tqdm
from datetime import datetime
from notion_client import Client
import altair as alt
import streamlit as st
from agno.tools import tool 
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.calculator import CalculatorTools
from urllib.parse import quote
import os

API_NOTION = "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"
DB_PESQUISAS = "208a0aa62a2e8071bf48eb14e2829daf"
DB_KEYWORDS = "208a0aa62a2e80938963e749a7a27bb5"
tqdm.pandas ()

def get_notion_client():
  return Client(auth=API_NOTION)

def extract_property_value(prop):
  prop_type = prop.get('type')
  value = prop.get(prop_type)

  if prop_type in ["title", "rich_text"]:
    return " ".join((t.get("plain_text", "") for t in value)) if value else None
  elif prop_type == "number":
    return value
  elif prop_type == "date":
    return value.get("start") if value else None
  else:
    return value

def notion_to_dataframe(response):
  """Lê uma resposta da API do Notion e retorna um dataframe"""
  rows = []
  for result in response.get("results", []):
    props = result.get("properties", {})
    row = {key: extract_property_value(prop) for key, prop in props.items()}
    rows.append(row)
  return pd.DataFrame(rows)

def insert_products_to_notion(df, db_id, notion_client):
  for _, row in df.iterrows(): # Recusa a primeira entrega, fica só com a segunda
    properties = {
        "Nome": {
            "type": "title",
            "title": [{"type": "text", "text": {"content": row["nome"]}}]
        },
        "Preço": {
            "type": "number",
            "number": float(row["preco"])
        },
        "URL": {
            "type": "url",
            "url": row["url"]
        },
        "Keyword": {
            "type": "rich_text",
            "rich_text": [{"type": "text", "text": {"content": row["keyword"]}}]
        },
        "Data": {
            "type": "date",
            "date": {"start": row["data"]}
        },
        "Timestamp": {
            "type": "rich_text",
            "rich_text": [{"type": "text", "text": {"content": row["timestamp"]}}]
        }}
    try:
      notion_client.pages.create(parent={"database_id": db_id},
                                   properties=properties)
    except Exception as e:
      print(e)

def insert_keywords_to_notion(keyword, db_id, notion_client):
  try:
    response = notion_client.databases.query(
        database_id=db_id,
        filter={
            "property": "Keyword",
            "title": {
                "equals": keyword
            }
        }
    )
    if response.get("results"):
      page_id = response.get("results")[0].get("id")
      notion_client.pages.update(
          page_id=page_id,
          properties={
              "Last Time": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}
                            }
          }
      )
    else:
      # Se não existir?
      notion_client.pages.create(
          parent={"database_id": db_id},
          properties={
              "Keyword": {"title": [{"text": {"content": keyword}}]},
              "Last Time": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}}
          }
      )
  except Exception as e:
    print(e)

def get_recent_keywords(notion_client, db_id, limit=30):
  """Busca keywords mais recentes"""
  try:
    response = notion_client.databases.query(
        database_id=db_id,
        sorts=[{"property": "Last Time", "direction": "descending"}],
        page_size=limit
    )
    keywords = []
    for result in response.get("results", []):
      title = result['properties']['Keywords']['title']
      if title:
        keywords.append(title[0]['plain_text'])
    return keywords
  except Exception as e:
    print(e)
    return []

@tool(name="Mercado Livre Scraper", description="Raspa produtos do Mercado Livre")
def mercado_livre_market_tools(produto):
  HEADERS = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
  }
  try:
    session = requests.Session()
    url = f"https://lista.mercadolivre.com.br/supermercado/market/{quote(produto.replace(' ', '-'))}"
    r = session.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    products = soup.find_all("div", {'class':"ui-search-result__wrapper"})

    produtos = []
    for product in products[:20]:
      nome = product.find("h3", {'class': 'poly-component__title-wrapper'}).get_text(strip=True)
      url_produto = product.find("h3").find('a').get('href')
      preco_text = product.find("span", {'class': 'andes-money-amount'}).get_text(strip=True)
      preco = float(preco_text.replace('R$', '').replace('.', '').replace(',', '.'))
      produtos.append({
          'nome': nome,
          'url': url_produto,
          'preco': preco,
          'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

  except:
    produtos = []

  return produtos

def get_produtos(produto):
  HEADERS = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
  }
  try:
    session = requests.Session()
    url = f"https://lista.mercadolivre.com.br/supermercado/market/{quote(produto.replace(' ', '-'))}"
    r = session.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    products = soup.find_all("div", {'class':"ui-search-result__wrapper"})

    produtos = []
    for product in products[:20]:
      nome = product.find("h3", {'class': 'poly-component__title-wrapper'}).get_text(strip=True)
      url_produto = product.find("h3").find('a').get('href')
      preco_text = product.find("span", {'class': 'andes-money-amount'}).get_text(strip=True)
      preco = float(preco_text.replace('R$', '').replace('.', '').replace(',', '.'))
      produtos.append({
          'nome': nome,
          'url': url_produto,
          'preco': preco,
          'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

  except:
    produtos = []

  return produtos


def verificar_raspagem_hoje(keyword, notion_client, db_id):
  try:
    hoje = datetime.now().strftime("%Y-%m-%d")

    response = notion_client.databases.query(
        database_id=db_id,
        filter={
            "and": [
                {
                    "property": "Keyword",
                    "rich_text": {
                        "equals": keyword
                    }
                },
                {
                    "property": "Data",
                    "date": {
                        "equals": hoje
                    }
                }
            ]
        }
    )

    return len(response.get("results", [])) > 0
  except Exception as e:
    print(e)
    return False

def get_dados_notion(keyword, notion_client, db_id):
  """Busca dados históricos do keyword no Notion"""
  try:
    response = notion_client.databases.query(
        database_id=db_id,
        filter={
            "property": "Keyword",
            "rich_text": {
                "equals": keyword
            }
        })
    return notion_to_dataframe(response)
  except Exception as e:
    print(e)
    return pd.DataFrame()

# Precisa de uma funcao pra criar grafico de precos, com a media, mediana, min, max e count

def preco_medio_atual(df):
  preco_medio = df["preco"].mean()
  return preco_medio

def preco_mediano_atual(df):
  preco_mediano = df["preco"].median()
  return preco_mediano

def menor_preco(df):
    if df.empty:
        return None, None, None
    min_idx = df['preco'].idxmin()
    min_row = df.loc[min_idx]
    return min_row['preco'], min_row['nome'], min_row['url']

def maior_preco(df):
    if df.empty:
        return None, None, None
    max_idx = df['preco'].idxmax()
    max_row = df.loc[max_idx]
    return max_row['preco'], max_row['nome'], max_row['url']



def criar_grafico_precos(df, keyword):
    """
    Cria um gráfico Altair de linha da tendência de preços a partir de um DataFrame
    com legendas e fundo branco.
    O DataFrame deve conter as colunas 'Data' e 'Preço'.
    """
    if df.empty or 'Data' not in df.columns or 'Preço' not in df.columns:
        print("O DataFrame está vazio ou não contém as colunas 'Data' e 'Preço'.")
        return None

    df['Data'] = pd.to_datetime(df['Data'])
    df['Preço'] = pd.to_numeric(df['Preço'], errors='coerce')
    df.dropna(subset=['Preço'], inplace=True)

    if df.empty:
         print("O DataFrame está vazio após a limpeza de dados não numéricos.")
         return None

    # Agregar dados por data para calcular estatísticas
    df_agg = df.groupby('Data')['Preço'].agg(['mean', 'median', 'min', 'max']).reset_index()

    # Para legendas, precisamos adicionar uma coluna 'Tipo' para cada estatística
    # e derreter o dataframe para um formato longo (long format)
    df_mean = df_agg.copy()
    df_mean['Tipo'] = 'Média'
    df_mean['Valor'] = df_mean['mean']

    df_median = df_agg.copy()
    df_median['Tipo'] = 'Mediana'
    df_median['Valor'] = df_median['median']

    df_min_max = df_agg.copy()
    # Criar uma coluna 'Tipo' para a área de variação (não aparecerá na legenda de cor, mas é útil para tooltips se necessário)
    df_min_max['Tipo'] = 'Variação (Mín-Máx)'


    # Combinar os dataframes para a linha de média e mediana
    df_lines = pd.concat([df_mean[['Data', 'Tipo', 'Valor']], df_median[['Data', 'Tipo', 'Valor']]])

    # Gráfico de linhas para média e mediana com legenda
    lines = alt.Chart(df_lines).mark_line(point=True).encode(
        x='Data:T',
        y='Valor:Q',
        color=alt.Color('Tipo:N', legend=alt.Legend(title="Estatística")), # Adiciona legenda com base na coluna 'Tipo'
        tooltip=[alt.Tooltip('Data:T'), alt.Tooltip('Tipo:N'), alt.Tooltip('Valor:Q', title='Preço')]
    ).properties(
        title=f'Tendência de Preços para: {keyword.title()}'
    )

    # Área para variação (min-max) - sem legenda de cor, pois é uma área
    variance_area = alt.Chart(df_min_max).mark_area(opacity=0.3).encode(
        x='Data:T',
        y='min:Q',
        y2='max:Q',
        tooltip=[alt.Tooltip('Data:T'), alt.Tooltip('min:Q', title='Mínimo'), alt.Tooltip('max:Q', title='Máximo')],
        color=alt.value('gray') # Cor da área de variação
    )

    # Combinar os gráficos
    chart = variance_area + lines

    # Configurar o fundo do gráfico
    chart = chart.configure_view(
        stroke=None # Remove a borda do gráfico
    ).configure_title(
        fontSize=16,
        anchor='start'
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    ).properties(
        background="white" # Define o fundo como branco
    )


    return chart.interactive() # Adiciona interatividade ao gráfico

def criar_grafico(df, keyword):
    """
    Cria um gráfico Altair com estatísticas de preço para um produto específico.

    Args:
        df (pd.DataFrame): DataFrame com os dados históricos do produto
        keyword (str): Nome do produto/keyword para título do gráfico

    Returns:
        alt.Chart: Objeto de gráfico Altair ou None se o DataFrame estiver vazio
    """
    # Esta verificação inicial está correta e já existe no código
    if df.empty or 'Data' not in df.columns or 'Preço' not in df.columns:
        print("O DataFrame está vazio ou não contém as colunas 'Data' e 'Preço'.")
        # Returning None or raising an error is better than continuing
        return None

    # CORREÇÃO: Use os nomes de coluna com letra maiúscula, como eles vêm do Notion
    # Ensure data types are correct for plotting and calculations
    df['Data'] = pd.to_datetime(df['Data'])
    # Adicionar manipulação de erro caso 'Preço' contenha valores não numéricos após extração
    df['Preço'] = pd.to_numeric(df['Preço'], errors='coerce')
    # Remover linhas onde a conversão para numérico falhou
    df.dropna(subset=['Preço'], inplace=True)


    # Check again if the DataFrame became empty after cleaning
    if df.empty:
         print("O DataFrame está vazio após a limpeza de dados não numéricos.")
         return None

    # Calcular estatísticas
    # Acessar as colunas 'Data' e 'Preço' com os nomes corrigidos (maiúsculos)
    stats = pd.DataFrame({
        'Estatística': ['Média', 'Mediana', 'Mínimo', 'Máximo'],
        'Preço (R$)': [
            df["Preço"].mean(), # Use 'Preço' (uppercase)
            df["Preço"].median(), # Use 'Preço' (uppercase)
            df["Preço"].min(), # Use 'Preço' (uppercase)
            df["Preço"].max() # Use 'Preço' (uppercase)
        ]
    })


    # Criar gráfico de barras
    bars = alt.Chart(df).mark_bar().encode(
        x=alt.X('Preço:Q', bin=True),
        y='count()',
        color=alt.Color('Preço', legend=None),
        tooltip=['Preço']
    ).properties(
        title=f'Estatísticas de Preço para: {keyword}',
        width=400,
        height=300
    )

    # Adicionar texto com os valores
    text = bars.mark_text(
        align='center',
        baseline='bottom',
        dy=-5
    ).encode(
        text=alt.Text('Preço:Q', format='.2f')
    )

    # Combinar gráficos
    chart = (bars + text).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    ).configure_title(
        fontSize=16,
        anchor='start'
    )

    return chart

def prever_preco_ewma(df, dias=7):
    try:
        df['Data'] = pd.to_datetime(df['Data'])
        df_diario = df.groupby('Data')['Preço'].mean().reset_index()
        df_diario = df_diario.sort_values('Data')
        
        ewma = df_diario['Preço'].ewm(span=dias, adjust=False).mean()
        return round(ewma.iloc[-1], 2)
    
    except Exception as e:
        st.error(f"Erro na previsão: {e}")
        return None

raspa_preco = Agent(
    name="MercadoLivre",
    model=Groq(id="meta-llama/llama-4-scout-17b-16e-instruct"),
    tools=[mercado_livre_market_tools, CalculatorTools()],
    description="Você é um agente que busca produtos no mercado livre",
    instructions=[
        "Você busca por produtos no site MercadoLivre.",
        "Você retorna os produtos encontrados",
        "Você deve retornar os produtos encontrados em formato de dicionário",
        "Esse dicionário deve conter as chaves: nome, url, preço, preço2",
        "A chave preço2 é o preço por quilo, litro ou unidade do produto, quando for o caso",
        "Retorne o preço em reais, e não esqueça de calcular o preço por quilo, litro ou unidade do produto, a depender do tipo de produto",
        "Retorne a timestamp também, conforme a ferramenta"
    ],
    markdown=False,
    debug_mode=False)

# Interface do Streamlit
st.title("📈 Sistema de Monitoramento de Preços")
st.markdown("""
    Rastreie preços de produtos no Mercado Livre e acompanhe tendências com previsões de preço.
""")

# Formulário de entrada
with st.form("product_form"):
    produto_input = st.text_input("Digite o produto para monitorar:")
    submitted = st.form_submit_button("Monitorar Produto")

if submitted:
    with st.spinner("Processando..."):
        try:
            # Inicializar cliente do Notion
            notion_client = get_notion_client()
            
            # Verificar se já foi raspado hoje
            ja_raspado = verificar_raspagem_hoje(produto_input, notion_client, DB_PESQUISAS)
            
            if not ja_raspado:
                # Coletar dados do Mercado Livre
                #df = get_produtos(produto_input)
                res = raspa_preco.run(produto_input)
                res = eval(res)
                df = pd.DataFrame(res)
                df[(df['preco2'] != 0) & (df['preco2'].notnull())]
                
                if not df.empty:
                    # Salvar no Notion
                    insert_products_to_notion(df, DB_PESQUISAS, notion_client)
                    insert_keywords_to_notion(produto_input, DB_KEYWORDS, notion_client)
                    st.success("Dados coletados e salvos no Notion!")
                else:
                    st.warning("Nenhum produto encontrado. Tente outro termo de busca.")
            else:
                st.info("Os dados deste produto já foram coletados hoje. Exibindo dados históricos.")
            
            # Obter dados históricos
            dados_historico = get_dados_notion(produto_input, notion_client, DB_PESQUISAS)
            
            if not dados_historico.empty:
                # Exibir dados recentes
                st.subheader("Produtos Encontrados Recentemente")
                st.dataframe(dados_historico[['Nome', 'Preço', 'Data']].head(10))
                
                # Mostrar estatísticas
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Preço Médio", f"R$ {dados_historico['Preço'].mean():.2f}")
                col2.metric("Preço Mediano", f"R$ {dados_historico['Preço'].median():.2f}")
                col3.metric("Menor Preço", f"R$ {dados_historico['Preço'].min():.2f}")
                col4.metric("Maior Preço", f"R$ {dados_historico['Preço'].max():.2f}")
                
                # Gerar gráficos
                st.subheader("Análise de Tendências")
                grafico = criar_grafico_precos(dados_historico, produto_input)
                grafico2 = criar_grafico(dados_historico, produto_input)
                if grafico:
                    st.altair_chart(grafico, use_container_width=True)
                    st.altair_chart(grafico2, use_container_width=True)
                else:
                    st.warning("Não há dados suficientes para gerar o gráfico de tendências.")
               
                
                # Fazer previsão
                st.subheader("Previsão de Preços")
                previsao_amanha = prever_preco_ewma(dados_historico)
                
                if previsao_amanha:
                    # Calcular variação
                    preco_atual = dados_historico['Preço'].mean()
                    variacao = ((previsao_amanha - preco_atual) / preco_atual) * 100
                    
                    st.metric(
                        label="Preço Médio Estimado para Amanhã", 
                        value=f"R$ {previsao_amanha:.2f}",
                        delta=f"{variacao:.1f}%"
                    )
                    
                    # Adicionar previsão ao gráfico
                    df_previsao = pd.DataFrame({
                        'Data': [datetime.now() + pd.Timedelta(days=1)],
                        'Tipo': ['Previsão'],
                        'Preço': [previsao_amanha]
                    })
                    
                    if grafico:
                        ponto_previsao = alt.Chart(df_previsao).mark_line(
                            size=100, color='red', shape='diamond'
                        ).encode(
                            x='Data:T',
                            y='Preço:Q',
                            tooltip=[alt.Tooltip('Data:T', format='%Y-%m-%d'), 
                                     alt.Tooltip('Preço:Q', title='Preço Previsto', format='$.2f')]
                        )
                        grafico_com_previsao = grafico + ponto_previsao
                        st.altair_chart(grafico_com_previsao, use_container_width=True)
            else:
                st.warning("Nenhum dado histórico encontrado para este produto.")
                
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
