from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

# Criar a aplicação Flask
app = Flask(__name__)

# Configuração do banco de dados
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, '../instance/investments.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'sua-chave-secreta-aqui'

# Inicializar o SQLAlchemy e Flask-Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Importar as rotas após inicializar o aplicativo e o banco de dados
# para evitar importações circulares
from app.routes import investment_routes