"""
Script para corrigir o campo has_market_price dos ativos no banco de dados.

Este script atualiza todos os ativos com tickers no formato tradicional (sem hífen)
para ter has_market_price=True, permitindo que o sistema busque as cotações em tempo real.
"""

import os
import sys
import re
from app import app, db
from app.models.investment import Asset

def fix_market_price_flags():
    print("Corrigindo flags de has_market_price no banco de dados...")
    
    # Buscar todos os ativos
    assets = Asset.query.all()
    
    # Contador para estatísticas
    updated_count = 0
    fixed_income_count = 0
    
    for asset in assets:
        # Se o ticker não contém hífen, é provavelmente um ativo negociado em mercado
        # E o ticker está no formato padrão (ex: PETR4, BBAS3, ITUB4, BOVA11...)
        if '-' not in asset.ticker:
            # Só atualizar se for None ou False
            if asset.has_market_price is None or asset.has_market_price is False:
                asset.has_market_price = True
                updated_count += 1
                print(f"Atualizando {asset.ticker} para has_market_price=True")
        else:
            # Garantir que ativos de renda fixa continuem marcados corretamente
            asset.has_market_price = False
            fixed_income_count += 1
            print(f"Mantendo {asset.ticker} como has_market_price=False (renda fixa)")
    
    # Salvar as mudanças
    db.session.commit()
    
    print(f"\nAtualização concluída!")
    print(f"- {updated_count} ativos de mercado atualizados para has_market_price=True")
    print(f"- {fixed_income_count} ativos de renda fixa confirmados como has_market_price=False")
    print("\nReinicie a aplicação para que as mudanças tenham efeito.")

if __name__ == "__main__":
    # Verificar se estamos no contexto da aplicação
    with app.app_context():
        fix_market_price_flags()