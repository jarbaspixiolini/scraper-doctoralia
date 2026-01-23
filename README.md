# scraper-doctoralia
Robô para buscar nome de especialidades e telefones de contato
Scraper de Profissionais - Doctoralia 🩺
Este projeto automatiza a coleta de dados de profissionais de saúde do portal Doctoralia. Ele foi desenvolvido para extrair informações estratégicas de médicos e clínicas com base em especialidade e convênio, consolidando os dados em uma planilha CSV pronta para uso no Excel ou Google Sheets.

📋 Funcionalidades
O script realiza o fluxo completo de navegação e extração:

Busca Automatizada: Identifica especialidade, cidade e convênio diretamente pela URL fornecida.

Scroll Infinito: Rola a página de resultados automaticamente para carregar todos os profissionais disponíveis.

Coleta de Perfis: Filtra e extrai links apenas de profissionais individuais e clínicas, ignorando páginas institucionais.

Extração de Dados Sensíveis:

Nome completo.

CRM e UF (via identificação de padrões de texto).

RQE (Registro de Qualificação de Especialista).

Endereço completo do consultório.

Telefones (clicando automaticamente no botão "Mostrar número" e tratando janelas flutuantes/modais).

Exportação Inteligente: Gera um arquivo CSV com codificação utf-8-sig para garantir a compatibilidade de acentos no Excel.

🛠️ Tecnologias Utilizadas
Python 3.9: Linguagem base do projeto.

Selenium WebDriver: Para automação da navegação e interação com elementos dinâmicos (cliques e scrolls).

WebDriver Manager: Gerenciamento automático do driver do Google Chrome.

RegEx (Expressões Regulares): Para limpeza e captura precisa de números de CRM e RQE no texto.

GitHub Actions: Para execução do robô diretamente nos servidores do GitHub, sem necessidade de manter o computador ligado.

🚀 Como Executar
Via GitHub Actions (Recomendado)
O projeto está configurado para rodar na nuvem do GitHub:

Vá até a aba Actions do seu repositório.

No menu lateral, selecione Executar Scraper Diario.

Clique no botão Run workflow.

Após a conclusão (ícone verde), o arquivo resultado_doctoralia.csv aparecerá atualizado na pasta principal do código (aba Code).
