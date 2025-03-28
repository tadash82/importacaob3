import sqlite3
import os
from app import app, db
from app.models.investment import Asset, Transaction

# Caminho do banco de dados - atualize para o caminho correto
DB_PATH = os.path.join('d:', 'desenvolvimento', 'financeiro', 'importacaob3', 'financeiro.db')

def fix_database():
    print(f"Iniciando correção/criação do banco de dados em: {DB_PATH}")
    
    # Verificar se o arquivo existe
    if not os.path.exists(DB_PATH):
        print(f"Banco de dados não encontrado em {DB_PATH}")
        
        # Verificar se o diretório app.instance_path existe
        instance_path = app.instance_path
        alternative_path = os.path.join(instance_path, 'financeiro.db')
        print(f"Tentando localizar em: {alternative_path}")
        
        if os.path.exists(alternative_path):
            print(f"Banco de dados encontrado em {alternative_path}")
            global DB_PATH
            DB_PATH = alternative_path
        else:
            print("Criando novo banco de dados...")
            with app.app_context():
                db.create_all()
                print("Tabelas criadas com sucesso!")
            return True
    
    # Fazer backup do banco de dados antes de alterá-lo
    backup_path = DB_PATH + '.backup'
    try:
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"Backup criado em: {backup_path}")
    except Exception as e:
        print(f"Aviso: Não foi possível criar backup: {str(e)}")
    
    # Conectar ao banco de dados
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verificar se a tabela asset existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='asset'")
    if not cursor.fetchone():
        print("Tabela 'asset' não existe. Vamos criá-la utilizando SQLAlchemy.")
        with app.app_context():
            db.create_all()
        print("Tabelas criadas com sucesso!")
        conn.close()
        return True
    
    # Verificar se as colunas já existem
    cursor.execute("PRAGMA table_info(asset)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    # Lista de colunas que precisamos adicionar
    new_columns = [
        ('has_market_price', 'BOOLEAN', '1'),  # Default é 1 (True)
        ('issuer', 'VARCHAR(100)', 'NULL'),
        ('maturity_date', 'DATE', 'NULL')
    ]
    
    # Adicionar colunas que não existem
    added_columns = []
    for col_name, col_type, default_value in new_columns:
        if col_name not in column_names:
            try:
                sql = f'ALTER TABLE asset ADD COLUMN {col_name} {col_type} DEFAULT {default_value}'
                cursor.execute(sql)
                added_columns.append(col_name)
                print(f"Coluna '{col_name}' adicionada com sucesso.")
            except sqlite3.OperationalError as e:
                print(f"Erro ao adicionar coluna '{col_name}': {str(e)}")
    
    # Confirmar alterações
    conn.commit()
    conn.close()
    
    if added_columns:
        print(f"Banco de dados atualizado com sucesso! Colunas adicionadas: {', '.join(added_columns)}")
    else:
        print("Nenhuma alteração necessária no banco de dados.")
    
    return True

if __name__ == "__main__":
    fix_database()
