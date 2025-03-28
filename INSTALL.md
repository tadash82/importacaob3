# Instruções de Instalação e Atualização

Este documento contém instruções para instalar e atualizar o Sistema de Controle de Investimentos.

## Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

## Instalação Inicial

1. Clone o repositório ou extraia os arquivos para a pasta desejada

2. (Recomendado) Crie um ambiente virtual Python:
   ```
   cd d:\desenvolvimento\financeiro\importacaob3
   python -m venv venv
   ```

3. Ative o ambiente virtual:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

5. Configure o banco de dados:
   ```
   python setup_db.py
   ```

6. Execute a aplicação:
   ```
   python run.py
   ```

7. Acesse a aplicação em seu navegador: http://localhost:5000

## Atualização para a Versão com Preços Atuais

Se você já tem uma versão anterior instalada e deseja atualizar para a versão que inclui preços atuais e cálculo de lucro/prejuízo, siga estas etapas:

1. Certifique-se de que seu ambiente virtual está ativado:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

2. Atualize as dependências:
   ```
   pip install -r requirements.txt
   ```

3. Verifique se a biblioteca yfinance está instalada corretamente:
   ```
   pip install yfinance --upgrade
   ```

4. Execute a aplicação:
   ```
   python run.py
   ```

## Solução de Problemas

### Erro ao buscar preços atuais

Se você estiver enfrentando problemas para obter os preços atuais dos ativos:

1. Verifique sua conexão com a internet

2. Verifique se a biblioteca yfinance está instalada:
   ```
   pip install yfinance
   ```

3. Para tickers brasileiros, certifique-se de que estão no formato correto (geralmente com sufixo .SA)

4. Se os FIIs não estiverem sendo cotados corretamente, tente adicionar manualmente o sufixo .SA nos tickers no arquivo `price_service.py`

### Outros problemas

Se você encontrar outros problemas:

1. Verifique os logs da aplicação
2. Limpe o cache do navegador
3. Reinicie a aplicação
