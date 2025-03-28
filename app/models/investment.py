from app import db
from datetime import datetime
import uuid

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(30), nullable=False, unique=True)  # Código do ativo (PETR4, BBAS3, etc.) ou identificador interno
    name = db.Column(db.String(100), nullable=False)  # Nome do ativo
    type = db.Column(db.String(50), nullable=False)  # Tipo de ativo (Ação, FII, Tesouro, etc.)
    sector = db.Column(db.String(100))  # Setor do ativo (Financeiro, Energia, etc.)
    has_market_price = db.Column(db.Boolean, default=True)  # Indica se o ativo tem cotação em mercado
    issuer = db.Column(db.String(100))  # Emissor do título (para renda fixa)
    maturity_date = db.Column(db.Date)  # Data de vencimento (para renda fixa)
    transactions = db.relationship('Transaction', backref='asset', lazy=True, cascade="all, delete-orphan")
    value_updates = db.relationship('AssetValueUpdate', backref='asset', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Asset {self.ticker}>'
    
    @staticmethod
    def generate_ticker_for_fixed_income(type, issuer=None):
        """Gera um ticker único para ativos de renda fixa"""
        prefix = type[:3].upper()  # Primeiras 3 letras do tipo (ex: LCA, CDB)
        if issuer:
            prefix += "-" + issuer[:3].upper()  # Primeiras 3 letras do emissor (ex: LCA-BRA para Bradesco)
        
        # Adicionar um código único para evitar duplicação
        unique_id = uuid.uuid4().hex[:6]
        return f"{prefix}-{unique_id}"
    
    def calculate_average_price(self):
        """Calcula o preço médio do ativo baseado nas transações."""
        total_quantity = 0
        total_investment = 0
        
        for transaction in self.transactions:
            if transaction.operation_type == 'compra':
                total_quantity += transaction.quantity
                total_investment += transaction.quantity * transaction.price
            elif transaction.operation_type == 'venda':
                total_quantity -= transaction.quantity
        
        if total_quantity > 0:
            return total_investment / total_quantity
        return 0
    
    def current_quantity(self):
        """Retorna a quantidade atual do ativo em carteira."""
        quantity = 0
        for transaction in self.transactions:
            if transaction.operation_type == 'compra':
                quantity += transaction.quantity
            elif transaction.operation_type == 'venda':
                quantity -= transaction.quantity
        return quantity
    
    def get_current_value(self):
        """Retorna o valor atual do ativo, se disponível."""
        # Se for um ativo de mercado, o valor atual é calculado pelo preço x quantidade
        if self.has_market_price:
            return self.calculate_average_price() * self.current_quantity()
        
        # Para renda fixa, retorna o valor mais recente registrado ou o valor original investido
        if not self.value_updates:
            return self.calculate_average_price() * self.current_quantity()
        
        # Retorna o valor mais recente registrado
        latest_update = AssetValueUpdate.query.filter_by(asset_id=self.id).order_by(AssetValueUpdate.date.desc()).first()
        if latest_update:
            return latest_update.current_value
        
        return self.calculate_average_price() * self.current_quantity()
    
    def calculate_yield(self):
        """Calcula o rendimento do ativo de renda fixa."""
        if not self.has_market_price:
            total_investment = self.calculate_average_price() * self.current_quantity()
            current_value = self.get_current_value()
            
            if total_investment > 0:
                return {
                    'total_investment': total_investment,
                    'current_value': current_value,
                    'absolute_yield': current_value - total_investment,
                    'percentage_yield': ((current_value / total_investment) - 1) * 100
                }
        
        return None

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.now().date())  # Data da operação
    operation_type = db.Column(db.String(20), nullable=False)  # Tipo de operação (compra ou venda)
    quantity = db.Column(db.Integer, nullable=False)  # Quantidade de ativos
    price = db.Column(db.Float, nullable=False)  # Preço unitário
    total_value = db.Column(db.Float, nullable=False)  # Valor total da operação
    taxes = db.Column(db.Float, default=0)  # Taxas e impostos
    notes = db.Column(db.Text)  # Observações
    
    def __repr__(self):
        return f'<Transaction {self.operation_type} {self.quantity} {self.asset.ticker} @ {self.price}>'
    
    def calculate_total(self):
        """Calcula o valor total da transação incluindo taxas."""
        return (self.quantity * self.price) + self.taxes

class AssetValueUpdate(db.Model):
    """Modelo para armazenar atualizações de valor de ativos de renda fixa."""
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.now().date())  # Data da atualização
    current_value = db.Column(db.Float, nullable=False)  # Valor atual do investimento
    notes = db.Column(db.Text)  # Observações (ex: fonte da informação, etc.)
    
    def __repr__(self):
        return f'<AssetValueUpdate {self.asset.ticker} @ {self.date}: R${self.current_value:.2f}>'