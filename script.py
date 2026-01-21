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

                # --- LÓGICA DO TELEFONE REVISADA ---
                tel = "Não revelado"
                try:
                    # Tenta encontrar o botão de mostrar telefone
                    btn = driver.find_element(By.PARTIAL_LINK_TEXT, "Mostrar número de telefone")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(2)
                    driver.execute_script("arguments[0].click();", btn)
                    
                    # Espera a animação do modal terminar
                    time.sleep(6) 
                    
                    # Busca o número dentro da modal usando seletores variados das suas imagens
                    # Tentativa 1: O <b> dentro da modal (sua 3ª imagem)
                    # Tentativa 2: Links que começam com 'tel:'
                    # Tentativa 3: Qualquer texto que tenha padrão de telefone (xx) xxxx-xxxx
                    
                    seletores_tel = [
                        "div.modal-content b", 
                        "b.text-nowrap", 
                        "a[data-tracking-id='phone-number']",
                        "span.phone-number"
                    ]
                    
                    for seletor in seletores_tel:
                        try:
                            el_tel = driver.find_element(By.CSS_SELECTOR, seletor)
                            if el_tel.text and "(" in el_tel.text:
                                tel = el_tel.text
                                break
                        except:
                            continue
                    
                    # Se ainda não achou, tenta pegar o número direto do link 'tel:' no código
                    if tel == "Não revelado":
                        link_tel = driver.find_element(By.XPATH, "//a[contains(@href, 'tel:')]")
                        tel = link_tel.get_attribute("href").replace("tel:", "")

                except Exception as e:
                    print(f"Aviso: Não conseguiu abrir o modal de telefone para {nome}")

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
