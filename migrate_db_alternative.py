from app import app, db
from app.models.investment import Asset, Transaction
import sqlite3

# Caminho para o banco de dados
db_path = 'instance/financeiro.db'  # Ajuste conforme necessário

# Conectar ao banco de dados
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Verificar se as colunas já existem
cursor.execute("PRAGMA table_info(asset)")
columns = cursor.fetchall()
column_names = [col[1] for col in columns]

# Adicionar colunas que não existem
if 'has_market_price' not in column_names:
    cursor.execute('ALTER TABLE asset ADD COLUMN has_market_price BOOLEAN DEFAULT 1')
    
if 'issuer' not in column_names:
    cursor.execute('ALTER TABLE asset ADD COLUMN issuer VARCHAR(100)')
    
if 'maturity_date' not in column_names:
    cursor.execute('ALTER TABLE asset ADD COLUMN maturity_date DATE')

# Definir todos os ativos existentes como tendo preço de mercado
cursor.execute('UPDATE asset SET has_market_price = 1')

# Confirmar e fechar
conn.commit()
conn.close()

print("Migração alternativa concluída com sucesso!")
