from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import time
import os
import traceback
import concurrent.futures
import threading

# Configurações
LINKEDIN_USERNAME = "wesleyinfo22@gmail.com"
LINKEDIN_PASSWORD = "Euseiasenha2982@"
SEARCH_KEYWORD = "Analista de Dados"
PAGES_TO_SCRAPE = 3  # Número de páginas para analisar
MAX_VAGAS_POR_PAGINA = 15  # Máximo de vagas para analisar por página
TEMPO_ESPERA_PADRAO = 2  # Tempo de espera padrão reduzido para tornar mais rápido

# Lista de habilidades/conhecimentos - substitua com suas habilidades
MINHAS_HABILIDADES = [
    "python", "sql", "análise de dados", "excel", "powerbi", "visualização", 
    "estatística", "pandas", "numpy", "machine learning", "banco de dados",
    "etl", "data mining", "tableau", "power bi", "bi", "business intelligence"
]

# Variável global para armazenar as vagas
todas_vagas = []
vagas_lock = threading.Lock()

def calcular_relevancia(descricao_vaga, habilidades):
    """
    Calcula a relevância da vaga com base nas habilidades do usuário.
    Retorna uma pontuação e as habilidades correspondentes encontradas.
    """
    pontuacao = 0
    habilidades_encontradas = []
    
    if not descricao_vaga:
        return pontuacao, habilidades_encontradas
        
    descricao_lower = descricao_vaga.lower()
    
    for habilidade in habilidades:
        if habilidade.lower() in descricao_lower:
            pontuacao += 1
            habilidades_encontradas.append(habilidade)
    
    return pontuacao, habilidades_encontradas

def safe_find_element(driver, by, value, wait_time=TEMPO_ESPERA_PADRAO):
    """Função para encontrar elemento com tratamento de erro"""
    try:
        element = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except:
        return None

def safe_find_elements(driver, by, value, wait_time=TEMPO_ESPERA_PADRAO):
    """Função para encontrar elementos com tratamento de erro"""
    try:
        elements = WebDriverWait(driver, wait_time).until(
            EC.presence_of_all_elements_located((by, value))
        )
        return elements
    except:
        return []

def safe_click(driver, element):
    """Função para clicar com tratamento de erro"""
    try:
        # Tenta clicar normalmente
        element.click()
        return True
    except ElementClickInterceptedException:
        try:
            # Tenta usar JavaScript para clicar se o clique normal falhar
            driver.execute_script("arguments[0].click();", element)
            return True
        except:
            return False
    except:
        return False

def analisar_vaga(driver, card, index, total):
    """Função para analisar uma vaga específica"""
    try:
        print(f"Analisando vaga {index}/{total}...")
        
        # Coleta informações básicas com múltiplas tentativas de seletores
        title_selectors = [".job-card-list__title", "a.job-card-container__link", ".job-card-container__link-wrapper", "h3"]
        company_selectors = [".job-card-container__company-name", ".job-card-container__primary-description", ".job-search-card__company-name", ".job-card-container__subtitle-link"]
        location_selectors = [".job-card-container__metadata-item", ".job-search-card__location", ".job-card-container__metadata-wrapper", "[class*='location']"]
        link_selectors = [".job-card-list__title", "a.job-card-container__link", "a"]
        
        # Obter título
        title = "Título não disponível"
        for selector in title_selectors:
            title_elem = safe_find_element(driver, By.CSS_SELECTOR, selector, wait_time=1)
            if title_elem:
                title = title_elem.text
                if title:
                    break
        
        # Obter empresa
        company = "Empresa não disponível"
        for selector in company_selectors:
            company_elem = safe_find_element(driver, By.CSS_SELECTOR, selector, wait_time=1)
            if company_elem:
                company = company_elem.text
                if company:
                    break
        
        # Obter localização
        location = "Localização não disponível"
        for selector in location_selectors:
            location_elem = safe_find_element(driver, By.CSS_SELECTOR, selector, wait_time=1)
            if location_elem:
                location = location_elem.text
                if location:
                    break
        
        # Obter link
        link = "Link não disponível"
        for selector in link_selectors:
            link_elem = safe_find_element(driver, By.CSS_SELECTOR, selector, wait_time=1)
            if link_elem:
                href = link_elem.get_attribute("href")
                if href:
                    link = href
                    break
        
        # Clica na vaga para obter a descrição detalhada
        clicked = safe_click(driver, card)
        
        descricao = ""
        if clicked:
            time.sleep(TEMPO_ESPERA_PADRAO)  # Tempo reduzido para acelerar
            
            # Tenta obter a descrição da vaga com diferentes seletores
            description_selectors = [
                ".jobs-description__content",
                ".jobs-description",
                ".jobs-details",
                "[class*='description']"
            ]
            
            for selector in description_selectors:
                descricao_element = safe_find_element(driver, By.CSS_SELECTOR, selector, wait_time=TEMPO_ESPERA_PADRAO)
                if descricao_element:
                    descricao = descricao_element.text
                    if descricao:
                        break
            
            if not descricao:
                descricao = "Descrição não disponível"
        else:
            descricao = "Não foi possível acessar a descrição"
        
        # Calcula a pontuação de relevância
        pontuacao, habilidades_encontradas = calcular_relevancia(descricao, MINHAS_HABILIDADES)
        
        # Cria o objeto de vaga
        vaga = {
            "titulo": title,
            "empresa": company,
            "localizacao": location,
            "link": link,
            "pontuacao": pontuacao,
            "habilidades_encontradas": habilidades_encontradas,
            "descricao": descricao[:300] + "..." if len(descricao) > 300 else descricao
        }
        
        # Adiciona à lista global de vagas com lock para thread safety
        with vagas_lock:
            todas_vagas.append(vaga)
            
        return True
        
    except Exception as e:
        print(f"Erro ao processar vaga {index}: {str(e)}")
        return False

def navegar_para_proxima_pagina(driver):
    """Navega para a próxima página de resultados"""
    try:
        # Tenta encontrar o botão de próxima página com diferentes seletores
        next_button_selectors = [
            "button[aria-label='Avançar']", 
            ".artdeco-pagination__button--next", 
            "li.artdeco-pagination__button--next button",
            "[data-test-pagination-page-btn='next']"
        ]
        
        for selector in next_button_selectors:
            next_button = safe_find_element(driver, By.CSS_SELECTOR, selector)
            if next_button and next_button.is_enabled():
                if safe_click(driver, next_button):
                    print("Navegando para a próxima página...")
                    time.sleep(TEMPO_ESPERA_PADRAO + 1)  # Um pouco mais de tempo para carregar a página
                    return True
        
        # Se chegou aqui, não conseguiu navegar
        print("Não foi possível navegar para a próxima página. Pode ser a última página.")
        return False
        
    except Exception as e:
        print(f"Erro ao navegar para próxima página: {str(e)}")
        return False

# Adicione esta função antes do main()
def calcular_porcentagem_match(pontuacao, total_habilidades):
    """Calcula a porcentagem de match com a vaga"""
    return (pontuacao / total_habilidades) * 100

def main():
    driver = None
    try:
        print("Iniciando o bot de busca de vagas no LinkedIn...")
        
        # Configuração do webdriver
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Tentativa de inicializar o driver
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"Método padrão falhou: {str(e)}")
            try:
                s = Service('chromedriver')  # Ajuste o caminho conforme necessário
                driver = webdriver.Chrome(service=s, options=chrome_options)
            except Exception as e:
                print(f"Método alternativo falhou: {str(e)}")
                raise Exception("Não foi possível inicializar o Chrome driver.")
        
        wait = WebDriverWait(driver, 15)  # Tempo de espera máximo reduzido
        
        # Login no LinkedIn
        print("Navegando para a página de login do LinkedIn...")
        driver.get("https://www.linkedin.com/login")
        time.sleep(TEMPO_ESPERA_PADRAO)
        
        print("Fazendo login...")
        username_field = safe_find_element(driver, By.ID, "username", wait_time=5)
        password_field = safe_find_element(driver, By.ID, "password", wait_time=5)
        
        if not username_field or not password_field:
            raise Exception("Não foi possível encontrar os campos de login.")
        
        username_field.send_keys(LINKEDIN_USERNAME)
        password_field.send_keys(LINKEDIN_PASSWORD)
        password_field.send_keys(Keys.RETURN)
        
        # Aguarda a página carregar após o login
        print("Aguardando carregamento após login...")
        time.sleep(TEMPO_ESPERA_PADRAO * 3)  # Um pouco mais de tempo para o login
        
        # Navega para busca de vagas
        print("Navegando para a página de busca de vagas...")
        driver.get("https://www.linkedin.com/jobs/search/")
        time.sleep(TEMPO_ESPERA_PADRAO)
        
        # Pesquisa por vagas
        print(f"Pesquisando por: {SEARCH_KEYWORD}")
        search_selectors = [
            "input[aria-label='Pesquisar cargo, competência ou empresa']",
            "input[placeholder='Pesquisar por cargo, competência ou empresa']",
            "input[class*='jobs-search-box__text-input']",
            "[class*='jobs-search-box'] input[type='text']"
        ]
        
        search_box = None
        for selector in search_selectors:
            search_box = safe_find_element(driver, By.CSS_SELECTOR, selector, wait_time=5)
            if search_box:
                break
        
        if not search_box:
            raise Exception("Não foi possível encontrar a caixa de pesquisa.")
        
        search_box.clear()
        search_box.send_keys(SEARCH_KEYWORD)
        search_box.send_keys(Keys.RETURN)
        print("Pesquisa enviada, aguardando resultados...")
        time.sleep(TEMPO_ESPERA_PADRAO * 2)
        
        # Loop para cada página a ser analisada
        for pagina_atual in range(1, PAGES_TO_SCRAPE + 1):
            print(f"\n{'='*50}")
            print(f"ANALISANDO PÁGINA {pagina_atual} DE {PAGES_TO_SCRAPE}")
            print(f"{'='*50}")
            
            # Scroll para carregar todas as vagas da página
            print("Fazendo scroll para carregar mais vagas...")
            for i in range(3):  # Reduzido para 3 scrolls
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(TEMPO_ESPERA_PADRAO)
            
            # Coleta de vagas
            print("Coletando lista de vagas desta página...")
            job_selectors = [
                ".jobs-search-results__list-item",
                ".job-card-container",
                ".job-search-card",
                "[data-job-id]"
            ]
            
            job_cards = []
            for selector in job_selectors:
                job_cards = safe_find_elements(driver, By.CSS_SELECTOR, selector)
                if job_cards:
                    break
            
            total_vagas_pagina = len(job_cards)
            print(f"Encontradas {total_vagas_pagina} vagas nesta página")
            
            if total_vagas_pagina == 0:
                print("Nenhuma vaga encontrada nesta página. Tentando próxima página...")
                if not navegar_para_proxima_pagina(driver):
                    break
                continue
            
            # Limitando o número de vagas a analisar por página
            vagas_a_analisar = min(MAX_VAGAS_POR_PAGINA, total_vagas_pagina)
            print(f"Analisando {vagas_a_analisar} vagas desta página...")
            
            # Analisa cada vaga da página
            for i, card in enumerate(job_cards[:vagas_a_analisar]):
                analisar_vaga(driver, card, i+1, vagas_a_analisar)
            
            # Verifica se deve continuar para a próxima página
            if pagina_atual < PAGES_TO_SCRAPE:
                if not navegar_para_proxima_pagina(driver):
                    print("Não há mais páginas disponíveis.")
                    break
            
        # Ordena as vagas pela pontuação em ordem decrescente
        with vagas_lock:
            vagas_pontuadas = sorted(todas_vagas, key=lambda x: x["pontuacao"], reverse=True)
        
        # Exibe as vagas mais compatíveis
        print("\n" + "="*80)
        print("VAGAS MAIS COMPATÍVEIS COM SUAS HABILIDADES")
        print("="*80)
        
        total_vagas_encontradas = len(vagas_pontuadas)
        print(f"Total de vagas analisadas: {total_vagas_encontradas}")
        
        if total_vagas_encontradas == 0:
            print("Nenhuma vaga foi encontrada ou analisada com sucesso.")
            return
        
        # Mostra as melhores vagas encontradas
        max_vagas_exibir = min(20, total_vagas_encontradas)
        print("\n🔍 RESULTADO DA ANÁLISE DE VAGAS")
        print(f"Total de vagas analisadas: {total_vagas_encontradas}")
        print("=" * 100)

        for i, vaga in enumerate(vagas_pontuadas[:max_vagas_exibir]):
            match_percentage = calcular_porcentagem_match(vaga['pontuacao'], len(MINHAS_HABILIDADES))
            
            print(f"\n📌 Vaga #{i+1}")
            print(f"🏢 Empresa: {vaga['empresa']}")
            print(f"💼 Cargo: {vaga['titulo']}")
            print(f"📍 Localização: {vaga['localizacao']}")
            print(f"🎯 Match com seu perfil: {match_percentage:.1f}%")
            print(f"✨ Relevância: {vaga['pontuacao']} de {len(MINHAS_HABILIDADES)} habilidades")
            
            if vaga['habilidades_encontradas']:
                print("\n🔑 Habilidades encontradas:")
                for skill in vaga['habilidades_encontradas']:
                    print(f"  ✓ {skill}")
            else:
                print("\n⚠️ Nenhuma habilidade específica encontrada na descrição.")
            
            print(f"\n🔗 Link da vaga: {vaga['link']}")
            
            print("\n📝 Prévia da descrição:")

        print("\nAnálise de vagas concluída com sucesso!")

    except Exception as e:
        print(f"Erro durante a execução: {str(e)}")
        print(traceback.format_exc())
    finally:
        if driver:
            print("Fechando o navegador...")
            driver.quit()

if __name__ == "__main__":
    main()