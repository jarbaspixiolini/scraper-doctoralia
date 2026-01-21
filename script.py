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
CIDADE = "" 
META = 5 
# --------------------

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
# ESTA LINHA É CRUCIAL: Engana o site fingindo ser um Windows real
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# Comando para esconder que é um robô (evita detecção básica)
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
  "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
})

def coletar():
    cidade_parte = f"/{CIDADE}" if CIDADE else ""
    url = f"https://www.doctoralia.com.br/{ESPECIALIDADE}{cidade_parte}/{CONVENIO}".replace("//", "/")
    
    print(f"Tentando acessar: {url}")
    driver.get(url)
    
    # Espera muito mais tempo (o site carrega verificações de bot no início)
    time.sleep(15) 
    
    # Tira um "print" imaginário da página para o log (ajuda a diagnosticar)
    print("Título da página atual:", driver.title)
    
    if "Verificação" in driver.title or "Just a moment" in driver.title:
        print("BLOQUEADO: O site pediu verificação de robô (Captcha).")
        return []
    try:
        btn_cookie = driver.find_element(By.ID, "onetrust-accept-btn-handler")
        btn_cookie.click()
        print("Cookies aceitos.")
    except:
        pass
    
    resultados = []
    links_processados = set()

    while len(resultados) < META:
        # Pega links específicos de perfis de médicos
        links_na_pagina = []
        elementos_a = driver.find_elements(By.CSS_SELECTOR, "a[data-test-id='doctor-name'], a[href*='/medico/']")
        
        for el in elementos_a:
            href = el.get_attribute("href")
            if href and "/medico/" in href and href not in links_processados:
                links_na_pagina.append(href)
                links_processados.add(href)
        
        # Remove duplicados mantendo a ordem
        links_na_pagina = list(dict.fromkeys(links_na_pagina))

        if not links_na_pagina:
            print("Nenhum link novo encontrado. Encerrando.")
            break

        for link in links_na_pagina:
            if len(resultados) >= META: break
            
            print(f"Processando: {link}")
            driver.get(link)
            time.sleep(10)
            
            try:
                corpo = driver.find_element(By.TAG_NAME, "body").text
                nome = driver.find_element(By.TAG_NAME, "h1").text
                
                # Busca CRM e RQE
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
                    # Rola até o botão para ele ficar visível
                    btn = driver.find_element(By.CSS_SELECTOR, "[data-test-id='show-phone-button']")
                    driver.execute_script("arguments[0].scrollIntoView();", btn)
                    time.sleep(10)
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(10)
                    tel_element = driver.find_element(By.CSS_SELECTOR, ".phone-number, [data-test-id='phone-number'], a[href^='tel:']")
                    tel = tel_element.text
                except: 
                    pass

                resultados.append({
                    "Nome": nome.strip(),
                    "CRM": crm.group(1) if crm else "N/A",
                    "RQE": rqe.group(1) if rqe else "N/A",
                    "Plano": CONVENIO.upper(),
                    "Telefone": tel.strip(),
                    "Endereço": endereco.replace("\n", " ").strip()
                })
                print(f"Sucesso: {nome}")
            except Exception as e:
                print(f"Erro no perfil: {e}")
                continue
            
            # Volta para a listagem
            driver.get(url)
            time.sleep(4)

        # Paginação
        try:
            btn_next = driver.find_element(By.CSS_SELECTOR, "[data-test-id='pagination-next']")
            driver.execute_script("arguments[0].click();", btn_next)
            url = driver.current_url # Atualiza a URL base para a próxima página
            time.sleep(10)
        except:
            print("Fim das páginas.")
            break

    return resultados

# Execução
try:
    dados = coletar()
    if dados:
        df = pd.DataFrame(dados)
        df.to_csv("resultado_doctoralia.csv", index=False, encoding='utf-8-sig')
        print(f"Processo finalizado com {len(dados)} contatos!")
    else:
        print("O script rodou mas não encontrou dados. Verifique os seletores.")
finally:
    driver.quit()
