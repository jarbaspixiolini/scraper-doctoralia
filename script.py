import time
import csv
import re
import argparse
from urllib.parse import urlparse, urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options

class DoctoraliaScraper:
    def __init__(self, headless=False):
        # Configurar Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        self.dados_profissionais = []
        self.links_coletados = set()  # Para evitar duplicatas entre páginas

    def extrair_info_url(self, url):
        """Extrai informações da URL para identificar o tipo de busca"""
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]

        # Identificar a especialidade/categoria na URL
        self.especialidade = path_parts[0] if path_parts else ''
        self.filtros = path_parts[1:] if len(path_parts) > 1 else []

        print(f"Especialidade detectada: {self.especialidade}")
        if self.filtros:
            print(f"Filtros detectados: {', '.join(self.filtros)}")

        return self.especialidade

    def scroll_para_carregar_todos(self, url):
        """Rola a página para carregar todos os profissionais (scroll infinito)"""
        print("Carregando página e fazendo scroll para carregar todos os profissionais...")
        self.driver.get(url)
        time.sleep(3)

        ultima_altura = self.driver.execute_script("return document.body.scrollHeight")
        tentativas_sem_mudanca = 0

        while tentativas_sem_mudanca < 3:
            # Rolar até o final
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Calcular nova altura
            nova_altura = self.driver.execute_script("return document.body.scrollHeight")

            # Se a altura não mudou, incrementar contador
            if nova_altura == ultima_altura:
                tentativas_sem_mudanca += 1
            else:
                tentativas_sem_mudanca = 0
                print("Carregando mais profissionais...")

            ultima_altura = nova_altura

    def obter_proxima_pagina(self):
        """Verifica se existe próxima página e retorna o link"""
        try:
            # Buscar botão/link de próxima página
            seletores_proxima = [
                'a[data-id="pagination-next"]',
                'a.next',
                'li.next a',
                'a[rel="next"]',
                '.pagination a:contains("Próxima")',
                '.pagination a:contains(">")',
                'a[aria-label="Next"]',
                'button[aria-label="Next"]'
            ]

            for seletor in seletores_proxima:
                try:
                    elementos = self.driver.find_elements(By.CSS_SELECTOR, seletor)
                    for elem in elementos:
                        href = elem.get_attribute('href')
                        if href and 'javascript' not in href.lower():
                            return href
                except:
                    continue

            # Tentar encontrar por texto
            links = self.driver.find_elements(By.TAG_NAME, 'a')
            for link in links:
                texto = link.text.strip().lower()
                if texto in ['próxima', 'próximo', 'next', '›', '»', '>']:
                    href = link.get_attribute('href')
                    if href and 'javascript' not in href.lower():
                        return href

            return None
        except Exception as e:
            print(f"Erro ao buscar próxima página: {e}")
            return None

    def obter_links_perfis_pagina_atual(self):
        """Extrai todos os links dos perfis de profissionais da página atual"""
        links = []

        # Seletores para encontrar cards/links de médicos
        # Os links de perfil geralmente estão em elementos com nome do médico
        seletores = [
            'a[data-doctor-id]',
            'a[data-id="doctor-name"]',
            '[data-id="search-list"] a',
            '.doctor-card a',
            'h3 a',
            '.h3 a',
            'a[href*="doctoralia.com.br/"]'
        ]

        elementos_encontrados = set()

        for seletor in seletores:
            try:
                elementos = self.driver.find_elements(By.CSS_SELECTOR, seletor)
                for elem in elementos:
                    elementos_encontrados.add(elem)
            except:
                continue

        for elemento in elementos_encontrados:
            try:
                href = elemento.get_attribute('href')
                if href and '/' in href:
                    # Remover query strings e hashes
                    href_limpo = href.split('?')[0].split('#')[0]

                    # Filtrar apenas perfis de profissionais
                    if self._eh_link_perfil_valido(href_limpo):
                        if href_limpo not in self.links_coletados:
                            links.append(href_limpo)
                            self.links_coletados.add(href_limpo)
            except:
                continue

        return links

    def _eh_link_perfil_valido(self, href):
        """Verifica se o link é um perfil válido de profissional"""
        # Deve ser do doctoralia
        if 'doctoralia.com.br' not in href:
            return False

        # Excluir links que não são perfis
        exclusoes = [
            '/clinicas/',
            '/centro-medico/',
            '/hospital/',
            '/social-connect/',
            '/entrar',
            '/cadastro',
            '/termos',
            '/privacidade',
            '/ajuda',
            '/sobre',
            '/contato',
            'google.com/maps'
        ]
        for exc in exclusoes:
            if exc in href.lower():
                return False

        # Extrair o path da URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(href)
            path = parsed.path.strip('/')
            partes = path.split('/')
        except:
            return False

        # Se o path tem pelo menos 2 partes e a primeira parte parece um nome de pessoa
        # Padrão: /nome-do-medico/especialidade/cidade
        # Exemplo: /alexandre-matone-2/endocrinologista-medico-clinico-geral/sao-paulo
        if len(partes) >= 2:
            primeira_parte = partes[0]

            # A primeira parte não deve ser uma especialidade ou filtro conhecido
            especialidades_comuns = [
                'endocrinologista', 'cardiologista', 'dermatologista', 'ginecologista',
                'ortopedista', 'pediatra', 'psiquiatra', 'neurologista', 'oftalmologista',
                'urologista', 'gastroenterologista', 'pneumologista', 'nefrologista',
                'reumatologista', 'otorrinolaringologista', 'medico', 'dentista',
                'psicologo', 'fisioterapeuta', 'nutricionista', 'fonoaudiologo'
            ]

            # Se a primeira parte for uma especialidade, não é um perfil individual
            if primeira_parte in especialidades_comuns:
                return False

            # Se a primeira parte contém hífen (nome composto) e tem pelo menos 2 partes no path
            # provavelmente é um perfil de médico
            if '-' in primeira_parte and len(partes) >= 2:
                # A segunda parte geralmente contém a especialidade
                segunda_parte = partes[1]
                # Verificar se a segunda parte parece uma especialidade
                for esp in especialidades_comuns:
                    if esp in segunda_parte:
                        return True

        return False

    def obter_links_perfis(self, url_base, limite=None):
        """Extrai todos os links dos perfis de todas as páginas"""
        print("Extraindo links dos perfis...")

        todos_links = []
        pagina_atual = 1
        url_atual = url_base

        while url_atual:
            print(f"\n--- Página {pagina_atual} ---")

            # Carregar página e fazer scroll
            self.scroll_para_carregar_todos(url_atual)

            # Coletar links desta página
            links_pagina = self.obter_links_perfis_pagina_atual()
            print(f"Perfis encontrados nesta página: {len(links_pagina)}")
            todos_links.extend(links_pagina)

            # Se tem limite e já coletou suficiente, parar
            if limite and len(todos_links) >= limite:
                print(f"Limite de {limite} perfis atingido. Parando coleta.")
                break

            # Verificar se há próxima página
            proxima = self.obter_proxima_pagina()

            if proxima and proxima != url_atual:
                url_atual = proxima
                pagina_atual += 1
                time.sleep(1)  # Pausa entre páginas
            else:
                url_atual = None

        print(f"\nTotal de perfis encontrados em {pagina_atual} página(s): {len(todos_links)}")
        return todos_links
    
    def extrair_dados_perfil(self, url):
        """Extrai todos os dados de um perfil individual"""
        print(f"\nProcessando: {url}")

        try:
            self.driver.get(url)
            time.sleep(2)

            dados = {
                'nome': '',
                'crm': '',
                'rqe': '',
                'telefones': [],
                'email': ''
            }

            # Extrair nome
            try:
                nome_elemento = self.wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, 'h1'))
                )
                dados['nome'] = nome_elemento.text.strip()
            except:
                dados['nome'] = 'N/A'

            # Extrair CRM e RQE
            texto_pagina = self.driver.find_element(By.TAG_NAME, 'body').text

            # Buscar CRM - formato: "CRM SP 74443" ou "CRM: SP 74443"
            crm_match = re.search(r'CRM[:\s]*([A-Z]{2})\s*(\d+[-]?\d*)', texto_pagina)
            if crm_match:
                dados['crm'] = f"CRM {crm_match.group(1)} {crm_match.group(2)}"

            # Buscar RQE (pode haver múltiplos) - formato: "RQE Nº: 15638" ou "RQE N°: 15638"
            rqe_matches = re.findall(r'RQE\s*[NnºÂ°]*[:\s]*(\d+)', texto_pagina)
            if rqe_matches:
                dados['rqe'] = ', '.join([f"RQE Nº: {rqe}" for rqe in rqe_matches])

            # Buscar email (geralmente não está disponível publicamente)
            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', texto_pagina)
            if email_match:
                dados['email'] = email_match.group(0)
            
            # Rolar para carregar a página completa
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)

            # Encontrar todos os botões "Mostrar número de telefone"
            # Usar JavaScript para encontrar botões que contenham o texto
            try:
                botoes_telefone = self.driver.execute_script("""
                    var botoes = [];
                    var allButtons = document.querySelectorAll('button');
                    allButtons.forEach(function(btn) {
                        if (btn.innerText && btn.innerText.includes('Mostrar número de telefone')) {
                            botoes.push(btn);
                        }
                    });
                    return botoes;
                """)

                print(f"  Encontrados {len(botoes_telefone)} botões de telefone")

                for i, botao in enumerate(botoes_telefone):
                    try:
                        # Rolar até o botão
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", botao)
                        time.sleep(0.5)

                        # Clicar no botão usando JavaScript
                        self.driver.execute_script("arguments[0].click();", botao)
                        time.sleep(1.5)

                        # Tentar extrair o telefone de várias formas
                        telefone_extraido = None

                        # Método 1: Buscar link tel: em modal ou dialog
                        try:
                            telefone_elemento = self.driver.find_element(
                                By.CSS_SELECTOR,
                                '[role="dialog"] a[href^="tel:"], .modal a[href^="tel:"], [data-modal] a[href^="tel:"]'
                            )
                            telefone_extraido = telefone_elemento.text.strip()
                        except:
                            pass

                        # Método 2: Buscar por padrão de telefone em qualquer modal/dialog visível
                        if not telefone_extraido:
                            try:
                                modais = self.driver.find_elements(
                                    By.CSS_SELECTOR,
                                    '[role="dialog"], .modal, [data-modal], .dp-modal'
                                )
                                for modal in modais:
                                    if modal.is_displayed():
                                        telefone_match = re.search(r'\(?\d{2}\)?\s*\d{4,5}[-\s]?\d{4}', modal.text)
                                        if telefone_match:
                                            telefone_extraido = telefone_match.group(0)
                                            break
                            except:
                                pass

                        # Método 3: Buscar em todo o body por telefone recém exibido
                        if not telefone_extraido:
                            try:
                                # Buscar links tel: visíveis
                                tel_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href^="tel:"]')
                                for tel in tel_links:
                                    if tel.is_displayed() and tel.text.strip():
                                        telefone_extraido = tel.text.strip()
                                        break
                            except:
                                pass

                        if telefone_extraido and telefone_extraido not in dados['telefones']:
                            dados['telefones'].append(telefone_extraido)
                            print(f"  Telefone {i+1}: {telefone_extraido}")

                        # Fechar o modal
                        try:
                            # Tentar vários seletores para fechar
                            fechar_seletores = [
                                'button[aria-label="Close"]',
                                'button[aria-label="Fechar"]',
                                '.modal button.close',
                                '[role="dialog"] button[class*="close"]',
                                '.dp-modal-close'
                            ]
                            for sel in fechar_seletores:
                                try:
                                    btn_fechar = self.driver.find_element(By.CSS_SELECTOR, sel)
                                    if btn_fechar.is_displayed():
                                        btn_fechar.click()
                                        time.sleep(0.3)
                                        break
                                except:
                                    continue
                            else:
                                # Se não encontrou botão, pressionar ESC
                                from selenium.webdriver.common.keys import Keys
                                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                                time.sleep(0.3)
                        except:
                            pass

                    except Exception as e:
                        print(f"  Erro ao processar botão de telefone {i+1}: {e}")
                        continue

            except Exception as e:
                print(f"  Erro ao buscar botões de telefone: {e}")
            
            return dados
        
        except Exception as e:
            print(f"Erro ao processar perfil: {e}")
            return None
    
    def gerar_nome_arquivo(self, url):
        """Gera um nome de arquivo baseado na URL"""
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]

        if path_parts:
            nome = '_'.join(path_parts)
            # Limitar tamanho e remover caracteres inválidos
            nome = re.sub(r'[^\w\-_]', '', nome)[:50]
            return f"doctoralia_{nome}.csv"
        return "doctoralia_profissionais.csv"

    def salvar_csv(self, nome_arquivo=None):
        """Salva os dados coletados em um arquivo CSV"""
        if not nome_arquivo:
            nome_arquivo = "doctoralia_profissionais.csv"

        print(f"\nSalvando dados em {nome_arquivo}...")

        with open(nome_arquivo, 'w', newline='', encoding='utf-8-sig') as arquivo:
            campos = ['Nome', 'CRM', 'RQE', 'Telefone(s)', 'Email', 'URL_Perfil']
            writer = csv.DictWriter(arquivo, fieldnames=campos)

            writer.writeheader()

            for dados in self.dados_profissionais:
                if dados:
                    writer.writerow({
                        'Nome': dados['nome'],
                        'CRM': dados['crm'],
                        'RQE': dados['rqe'],
                        'Telefone(s)': ' | '.join(dados['telefones']) if dados['telefones'] else 'N/A',
                        'Email': dados['email'] if dados['email'] else 'N/A',
                        'URL_Perfil': dados.get('url', 'N/A')
                    })

        print(f"Arquivo salvo com sucesso! Total de profissionais: {len(self.dados_profissionais)}")
    
    def executar(self, url, limite=None, nome_arquivo=None):
        """Executa o processo completo de scraping"""
        try:
            # Validar URL
            if not self._validar_url(url):
                print("ERRO: URL inválida. Use uma URL do Doctoralia.")
                return

            # Extrair informações da URL
            self.extrair_info_url(url)

            # Gerar nome do arquivo se não fornecido
            if not nome_arquivo:
                nome_arquivo = self.gerar_nome_arquivo(url)

            # Passo 1 e 2: Obter links dos perfis (com paginação e limite)
            links_perfis = self.obter_links_perfis(url, limite=limite)

            if not links_perfis:
                print("\nNenhum perfil encontrado. Verifique a URL.")
                return

            # Aplicar limite final (caso tenha coletado mais que o necessário na última página)
            if limite and len(links_perfis) > limite:
                links_perfis = links_perfis[:limite]

            # Passo 3: Processar cada perfil
            print(f"\nIniciando coleta de dados de {len(links_perfis)} perfis...\n")

            for i, link in enumerate(links_perfis, 1):
                print(f"[{i}/{len(links_perfis)}]", end=" ")
                dados = self.extrair_dados_perfil(link)
                if dados:
                    dados['url'] = link  # Adicionar URL do perfil aos dados
                    self.dados_profissionais.append(dados)

                # Pequena pausa entre requisições para não sobrecarregar o servidor
                time.sleep(1)

            # Passo 4: Salvar em CSV
            self.salvar_csv(nome_arquivo)

        finally:
            self.driver.quit()

    def _validar_url(self, url):
        """Valida se a URL é do Doctoralia"""
        try:
            parsed = urlparse(url)
            return 'doctoralia.com.br' in parsed.netloc
        except:
            return False


# Uso do script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Scraper de profissionais do Doctoralia',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemplos de uso:
  python scrapper_doctoralia.py "https://www.doctoralia.com.br/endocrinologista/amil"
  python scrapper_doctoralia.py "https://www.doctoralia.com.br/cardiologista/sao-paulo" --limite 10
  python scrapper_doctoralia.py "https://www.doctoralia.com.br/dermatologista" --output dermatologistas.csv
  python scrapper_doctoralia.py "https://www.doctoralia.com.br/psiquiatra/unimed" --headless
        '''
    )

    parser.add_argument('url', nargs='?',
                        help='URL do Doctoralia para fazer scraping')
    parser.add_argument('--limite', '-l', type=int,
                        help='Limitar número de perfis a processar (útil para testes)')
    parser.add_argument('--output', '-o',
                        help='Nome do arquivo CSV de saída')
    parser.add_argument('--headless', action='store_true',
                        help='Executar sem abrir janela do navegador')

    args = parser.parse_args()

    print("=" * 60)
    print("SCRAPER DE PROFISSIONAIS - DOCTORALIA")
    print("=" * 60)

    # Se não passou URL como argumento, pedir interativamente
    if not args.url:
        print("\nNenhuma URL fornecida como argumento.")
        print("Por favor, insira a URL do Doctoralia que deseja fazer scraping.")
        print("Exemplos:")
        print("  - https://www.doctoralia.com.br/endocrinologista/amil")
        print("  - https://www.doctoralia.com.br/cardiologista/sao-paulo")
        print("  - https://www.doctoralia.com.br/dermatologista")
        print()
        url = input("URL: ").strip()
    else:
        url = args.url

    if not url:
        print("ERRO: URL não fornecida.")
        exit(1)

    print(f"\nURL: {url}")
    if args.limite:
        print(f"Limite: {args.limite} perfis")
    if args.output:
        print(f"Arquivo de saída: {args.output}")
    if args.headless:
        print("Modo: headless (sem janela)")
    print()

    scraper = DoctoraliaScraper(headless=args.headless)
    scraper.executar(url, limite=args.limite, nome_arquivo=args.output)

    print("\n" + "=" * 60)
    print("PROCESSO CONCLUÍDO!")
    print("=" * 60)
