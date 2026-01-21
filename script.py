import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import re

# --- CONFIGURAÇÃO ---
ESPECIALIDADE = "psiquiatra"
CONVENIO = "unimed"
META = 15 
# --------------------

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def coletar():
    url = f"https://www.doctoralia.com.br/{ESPECIALIDADE}/{CONVENIO}"
    driver.get(url)
    time.sleep(8)
    
    resultados = []
    links_processados = set()

    while len(resultados) < META:
        # Pega os links usando o seletor da sua primeira imagem
        elementos_nome = driver.find_elements(By.CSS_SELECTOR, "span[data-tracking-id='result-card-name']")
        
        links_da_pagina = []
        for el in elementos_nome:
            try:
                # Sobe dois níveis no código para achar o link <a> que envolve o nome
                ancora = el.find_element(By.XPATH, "./..")
                link = ancora.get_attribute("href")
                if link and link not in links_processados:
                    links_da_pagina.append(link)
                    links_processados.add(link)
            except: continue

        if not links_da_pagina: break

        for link in links_da_pagina:
            if len(resultados) >= META: break
            driver.get(link)
            time.sleep(5)
            
            try:
                nome = driver.find_element(By.TAG_NAME, "h1").text
                corpo = driver.find_element(By.TAG_NAME, "body").text
                
                # CRM e RQE via texto
                crm = re.search(r"CRM\s*[:\-\s]*([A-Z]*\s*\d+)", corpo)
                rqe = re.search(r"RQE\s*[:\-\s]*(\d+)", corpo)
                
                # Endereço
                try:
                    endereco = driver.find_element(By.CLASS_NAME, "location-address").text
                except: endereco = "Não encontrado"

                # TELEFONE (Ajustado para esperar a janela flutuante abrir)
                tel = "Não revelado"
                try:
                    # 1. Tenta clicar no link que você mostrou na imagem
                    btn = driver.find_element(By.PARTIAL_LINK_TEXT, "Mostrar número de telefone")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", btn)
                    
                    # 2. ESPERA a janelinha (modal) aparecer
                    time.sleep(4) 
                    
                    # 3. Tenta capturar o número de 3 formas diferentes dentro da janela
                    try:
                        # Forma 1: Pelo negrito <b> que você mostrou na 3ª imagem
                        tel_elemento = driver.find_element(By.CSS_SELECTOR, "div.modal-content b")
                        tel = tel_elemento.text
                    except:
                        try:
                            # Forma 2: Pelo link de telefone (tel:)
                            tel_elemento = driver.find_element(By.CSS_SELECTOR, "a[href^='tel:']")
                            tel = tel_elemento.text
                        except:
                            # Forma 3: Pela classe genérica de número
                            tel_elemento = driver.find_element(By.CLASS_NAME, "phone-number")
                            tel = tel_elemento.text
                except:
                    pass

                resultados.append({
                    "Nome": nome,
                    "CRM": crm.group(1) if crm else "N/A",
                    "RQE": rqe.group(1) if rqe else "N/A",
                    "Plano": CONVENIO.upper(),
                    "Telefone": tel,
                    "Endereço": endereco.replace("\n", " ")
                })
                print(f"Sucesso: {nome}")
            except: continue
            
            driver.get(url) # Volta para a lista
            time.sleep(4)

        # Próxima página
        try:
            btn_next = driver.find_element(By.CSS_SELECTOR, "[data-test-id='pagination-next']")
            driver.execute_script("arguments[0].click();", btn_next)
            url = driver.current_url
            time.sleep(6)
        except: break

    return resultados

dados = coletar()
if dados:
    pd.DataFrame(dados).to_csv("resultado_doctoralia.csv", index=False, encoding='utf-8-sig')
driver.quit()
