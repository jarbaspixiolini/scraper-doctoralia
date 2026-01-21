import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# Configuração do Navegador (Modo Invisível para o GitHub)
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# URL filtrada para Psiquiatria + Unimed
url_base = "https://www.doctoralia.com.br/psiquiatra/unimed"

def coletar_dados():
    driver.get(url_base)
    time.sleep(5) # Espera o site carregar
    
    medicos = []
    # Busca os cards dos médicos (limitado aos 5 primeiros para teste)
    cards = driver.find_elements(By.CSS_SELECTOR, "[data-test-id='search-results-item']")[:5]
    
    for card in cards:
        try:
            nome = card.find_element(By.CSS_SELECTOR, "h3").text
            link = card.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
            medicos.append({"Nome": nome, "Link": link})
        except:
            continue

    # Agora entra em cada link para pegar endereço e telefone
    lista_final = []
    for m in medicos:
        driver.get(m['Link'])
        time.sleep(3)
        try:
            endereco = driver.find_element(By.CLASS_NAME, "location-address").text
            # Tenta clicar no botão de telefone se existir
            try:
                btn = driver.find_element(By.CSS_SELECTOR, "[data-test-id='show-phone-button']")
                btn.click()
                time.sleep(1)
                tel = driver.find_element(By.CLASS_NAME, "phone-number").text
            except:
                tel = "Não disponível"
                
            lista_final.append({
                "Nome": m['Nome'],
                "Telefone": tel,
                "Endereço": endereco
            })
        except:
            continue
            
    return lista_final

# Executa e salva em Excel
dados = coletar_dados()
df = pd.DataFrame(dados)
df.to_csv("resultado_doctoralia.csv", index=False)
print("Arquivo gerado com sucesso!")
driver.quit()
