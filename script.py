import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================================
# CONFIGURAÇÃO DE BUSCA - ALTERE APENAS AQUI
# ==========================================================
ESPECIALIDADE = "psiquiatra"
CONVENIO = "unimed"
CIDADE = "" 
META_CONTATOS = 50  # O robô tentará coletar até 50 contatos
# ==========================================================

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
wait = WebDriverWait(driver, 10)

def extrair_dados_perfil(url_perfil):
    driver.get(url_perfil)
    time.sleep(3)
    dados = {"Link": url_perfil, "Nome": "N/A", "CRM": "N/A", "RQE": "N/A", "Telefone": "N/A", "Endereço": "N/A"}
    
    try:
        # Nome
        dados["Nome"] = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).text
        
        # Endereço
        try:
            dados["Endereço"] = driver.find_element(By.CLASS_NAME, "location-address").text.replace("\n", " ")
        except: pass

        # CRM e RQE (Geralmente em um subtítulo ou seção de registros)
        try:
            texto_pagina = driver.find_element(By.TAG_NAME, "body").text
            import re
            crm_match = re.search(r"CRM\s*[:\-\s]*(\d+)", texto_pagina)
            rqe_match = re.search(r"RQE\s*[:\-\s]*(\d+)", texto_pagina)
            if crm_match: dados["CRM"] = crm_match.group(1)
            if rqe_match: dados["RQE"] = rqe_match.group(1)
        except: pass

        # Telefone (Clica para revelar)
        try:
            btn_tel = driver.find_element(By.CSS_SELECTOR, "[data-test-id='show-phone-button']")
            driver.execute_script("arguments[0].click();", btn_tel)
            time.sleep(2)
            tel_element = driver.find_element(By.CSS_SELECTOR, "span.phone-number, a.phone-number")
            dados["Telefone"] = tel_element.text
        except: pass
        
    except Exception as e:
        print(f"Erro ao extrair perfil: {url_perfil}")
    
    return dados

def iniciar_scraping():
    url_base = f"https://www.doctoralia.com.br/{ESPECIALIDADE}/{CIDADE}/{CONVENIO}".replace("//", "/")
    driver.get(url_base)
    
    resultados = []
    
    while len(resultados) < META_CONTATOS:
        time.sleep(5)
        # Coleta links da página atual
        links_na_pagina = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "h3 a") or driver.find_elements(By.CSS_SELECTOR, "[data-test-id='search-results-item'] a")]
        links_unicos = list(dict.fromkeys(links_na_pagina)) # Remove duplicados
        
        print(f"Encontrados {len(links_unicos)} profissionais nesta página...")

        for link in links_unicos:
            if len(resultados) >= META_CONTATOS: break
            print(f"Coletando ({len(resultados)+1}/{META_CONTATOS}): {link}")
            info = extrair_dados_perfil(link)
            info["Plano"] = CONVENIO.upper()
            resultados.append(info)
            driver.back() # Volta para a lista
            time.sleep(2)

        # Tenta ir para a próxima página se não atingiu a meta
        if len(resultados) < META_CONTATOS:
            try:
                btn_proximo = driver.find_element(By.CSS_SELECTOR, "[data-test-id='pagination-next']")
                driver.execute_script("arguments[0].click();", btn_proximo)
                print("Indo para a próxima página...")
            except:
                print("Fim das páginas disponíveis.")
                break
                
    return resultados

# Execução
dados_finais = iniciar_scraping()
df = pd.DataFrame(dados_finais)
df.to_csv("resultado_doctoralia.csv", index=False, encoding='utf-8-sig')
print(f"Processo concluído! {len(dados_finais)} contatos salvos.")
driver.quit()
