import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

# --- CONFIGURAÇÃO ---
ESPECIALIDADE = "psiquiatra"
CONVENIO = "unimed"
META = 30 
# --------------------

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
wait = WebDriverWait(driver, 10)

def coletar():
    url_base = f"https://www.doctoralia.com.br/{ESPECIALIDADE}/{CONVENIO}"
    driver.get(url_base)
    time.sleep(8)
    
    resultados = []
    links_processados = set()

    while len(resultados) < META:
        # Pega os links dos nomes dos médicos (conforme sua 1ª imagem)
        elementos_nome = driver.find_elements(By.CSS_SELECTOR, "span[data-tracking-id='result-card-name']")
        links_da_pagina = []
        for el in elementos_nome:
            try:
                ancora = el.find_element(By.XPATH, "./..")
                link = ancora.get_attribute("href")
                if link and link not in links_processados:
                    links_da_pagina.append(link)
                    links_processados.add(link)
            except: continue

        if not links_da_pagina: break

        for link in links_da_pagina:
            if len(resultados) >= META: break
            print(f"Acessando perfil: {link}")
            driver.get(link)
            time.sleep(6)
            
            try:
                nome = driver.find_element(By.TAG_NAME, "h1").text
                corpo = driver.find_element(By.TAG_NAME, "body").text
                
                # CRM e RQE (via texto)
                crm = re.search(r"CRM\s*[:\-\s]*([A-Z]*\s*\d+)", corpo)
                rqe = re.search(r"RQE\s*[:\-\s]*(\d+)", corpo)
                
                # --- LÓGICA DO ENDEREÇO (Corrigida para evitar 'Psiquiatra · Mais') ---
                endereco = "Endereço não localizado"
                try:
                    # Busca especificamente pela classe de endereço ou texto dentro do bloco de consulta
                    end_el = driver.find_element(By.CSS_SELECTOR, ".location-address, [data-test-id='address-text']")
                    endereco = end_el.text.replace("\n", " ").strip()
                except: pass

                # --- LÓGICA DO TELEFONE (Específica para a Modal do vídeo) ---
                tel = "Não revelado"
                try:
                    # Clica no botão (conforme sua 2ª imagem)
                    btn = driver.find_element(By.PARTIAL_LINK_TEXT, "Mostrar número de telefone")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", btn)
                    
                    # Espera a Modal abrir (conforme seu vídeo)
                    time.sleep(5)
                    
                    # Procura o número que está dentro do <b> e do link 'tel:' (conforme sua 3ª imagem)
                    links_tel = driver.find_elements(By.CSS_SELECTOR, "a[href^='tel:']")
                    for l in links_tel:
                        # Pega o primeiro link visível que contenha um número
                        texto_tel = l.text.strip()
                        if texto_tel and "(" in texto_tel:
                            tel = texto_tel
                            break
                    
                    # Se não achou pelo texto, extrai direto do atributo 'href'
                    if tel == "Não revelado" and links_tel:
                        tel = links_tel[0].get_attribute("href").replace("tel:", "")
                except: pass

                resultados.append({
                    "Nome": nome,
                    "CRM": crm.group(1) if crm else "N/A",
                    "RQE": rqe.group(1) if rqe else "N/A",
                    "Plano": CONVENIO.upper(),
                    "Telefone": tel,
                    "Endereço": endereco
                })
                print(f"OK: {nome} | Tel: {tel}")
            except: continue
            
            # Volta para a listagem (mais estável que driver.back())
            driver.get(url_base)
            time.sleep(5)

        # Paginação
        try:
            btn_next = driver.find_element(By.CSS_SELECTOR, "[data-test-id='pagination-next']")
            driver.execute_script("arguments[0].click();", btn_next)
            url_base = driver.current_url
            time.sleep(6)
        except: break

    return resultados

# Executa e salva
dados = coletar()
if dados:
    df = pd.DataFrame(dados)
    df.to_csv("resultado_doctoralia.csv", index=False, encoding='utf-8-sig')
    print("Planilha gerada com sucesso!")
driver.quit()
