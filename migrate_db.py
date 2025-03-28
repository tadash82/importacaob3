from app import app, db
from app.models.investment import Asset, Transaction
from flask_migrate import Migrate, upgrade

migrate = Migrate(app, db)

with app.app_context():
    # Adicione as novas colunas à tabela
    # Essa abordagem é para SQLite - para outros bancos pode ser diferente
    if not hasattr(Asset, 'has_market_price'):
        db.engine.execute('ALTER TABLE asset ADD COLUMN has_market_price BOOLEAN DEFAULT 1')
    
    if not hasattr(Asset, 'issuer'):
        db.engine.execute('ALTER TABLE asset ADD COLUMN issuer VARCHAR(100)')
    
    if not hasattr(Asset, 'maturity_date'):
        db.engine.execute('ALTER TABLE asset ADD COLUMN maturity_date DATE')
    
    # Definir todos os ativos existentes como tendo preço de mercado
    db.engine.execute('UPDATE asset SET has_market_price = 1')
    
    db.session.commit()
    print("Migração concluída com sucesso!")
