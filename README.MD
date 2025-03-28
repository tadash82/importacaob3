# Gerenciador de Investimentos

Este é um projeto profissional em Python para gerenciar investimentos, com as seguintes funcionalidades:

- Importação de extratos da B3.
- Controle de ações, FIIs, renda fixa, investimentos internacionais e outros.
- Adicionar, remover e editar investimentos.

## Estrutura do Projeto

O projeto utiliza Flask como framework web e um banco de dados relacional para armazenar os dados. A estrutura foi projetada para ser modular e expansível, permitindo fácil manutenção e inclusão de novas funcionalidades.

## Requisitos

- Python 3.9 ou superior
- Flask
- SQLAlchemy

## Configuração Inicial

1. Clone este repositório.
2. Instale as dependências com `pip install -r requirements.txt`.
3. Execute o servidor com `flask run`.

## Estrutura de Pastas

- `app/`: Contém o código principal do aplicativo.
  - `models/`: Modelos do banco de dados.
  - `routes/`: Rotas da aplicação.
  - `templates/`: Templates HTML.
  - `static/`: Arquivos estáticos (CSS, JS, imagens).
- `tests/`: Testes automatizados.
- `migrations/`: Arquivos de migração do banco de dados.

## Próximos Passos

- Implementar a importação de extratos da B3.
- Criar interface para gerenciamento de investimentos.