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
META = 50 
# --------------------

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def coletar():
    url = f"https://www.doctoralia.com.br/{ESPECIALIDADE}/{CONVENIO}"
    driver.get(url)
    time.sleep(5)
    
    resultados = []
    links_processados = set()

    while len(resultados) < META:
        # Encontra todos os links que levam para perfis de médicos
        todos_links = driver.find_elements(By.TAG_NAME, "a")
        links_medicos = []
        
        for l in todos_links:
            href = l.get_attribute("href")
            if href and "/medico/" in href and href not in links_processados:
                links_medicos.append(href)
                links_processados.add(href)

        if not links_medicos:
            print("Não encontrei novos links na página.")
            break

        for link in links_medicos:
            if len(resultados) >= META: break
            
            driver.get(link)
            time.sleep(4)
            
            try:
                corpo = driver.find_element(By.TAG_NAME, "body").text
                nome = driver.find_element(By.TAG_NAME, "h1").text
                
                # Busca CRM e RQE com filtros de texto
                crm = re.search(r"CRM\s*[:\-\s]*(\d+)", corpo)
                rqe = re.search(r"RQE\s*[:\-\s]*(\d+)", corpo)
                
                # Endereço
                try:
                    endereco = driver.find_element(By.CLASS_NAME, "location-address").text
                except:
                    endereco = "Não listado"

                # Telefone
                tel = "Não revelado"
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, "[data-test-id='show-phone-button']")
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(2)
                    tel = driver.find_element(By.CSS_SELECTOR, ".phone-number, [data-test-id='phone-number']").text
                except: pass

                resultados.append({
                    "Nome": nome,
                    "CRM": crm.group(1) if crm else "N/A",
                    "RQE": rqe.group(1) if rqe else "N/A",
                    "Plano": CONVENIO.upper(),
                    "Telefone": tel,
                    "Endereço": endereco.replace("\n", " ")
                })
                print(f"Coletado: {nome}")
            except:
                continue
            
            driver.back()
            time.sleep(2)

        # Tenta próxima página
        try:
            btn_next = driver.find_element(By.CSS_SELECTOR, "[data-test-id='pagination-next']")
            driver.execute_script("arguments[0].click();", btn_next)
            time.sleep(5)
        except:
            break

    return resultados

dados = coletar()
if dados:
    df = pd.DataFrame(dados)
    df.to_csv("resultado_doctoralia.csv", index=False, encoding='utf-8-sig')
    print("Arquivo gerado com sucesso!")
driver.quit()
