from flask import request, jsonify, render_template, redirect, url_for, flash
from app import app, db
from app.models.investment import Asset, Transaction, AssetValueUpdate
from datetime import datetime
import pandas as pd
import os
import logging
from app.services.price_service import get_current_prices  # Corrigindo a importação

# Configurar logging
logger = logging.getLogger(__name__)


def normalize_ticker(ticker):
    """
    Normaliza um ticker removendo o sufixo 'F' de ativos fracionários.
    Ex: TAEE11F -> TAEE11
    """
    return ticker[:-1] if ticker.endswith("F") and len(ticker) > 1 else ticker


@app.route("/")
def home():
    assets = Asset.query.all()

    # Agrupar ativos pelo ticker normalizado
    assets_by_ticker = {}

    for asset in assets:
        normalized_ticker = normalize_ticker(asset.ticker)

        # Se o ticker não existe no dicionário, cria uma entrada nova
        if normalized_ticker not in assets_by_ticker:
            assets_by_ticker[normalized_ticker] = {
                "assets": [],
                "quantity": 0,
                "total_investment": 0,
                "name": asset.name,
                "type": asset.type,
            }

        # Adiciona o asset ao grupo
        assets_by_ticker[normalized_ticker]["assets"].append(asset)

        # Acumula quantidade e valor
        quantity = asset.current_quantity()
        if quantity > 0:
            avg_price = asset.calculate_average_price()
            asset_value = quantity * avg_price

            assets_by_ticker[normalized_ticker]["quantity"] += quantity
            assets_by_ticker[normalized_ticker]["total_investment"] += asset_value

    # Constrói a lista de portfolio agrupada
    portfolio_data = []
    total_value = 0
    tipos_ativos = set()  # Conjunto para armazenar os tipos únicos de ativos

    for normalized_ticker, data in assets_by_ticker.items():
        if data["quantity"] > 0:
            total_investment = data["total_investment"]
            total_value += total_investment

            # Usar o nome do primeiro ativo no grupo (geralmente serão iguais)
            name = data["assets"][0].name if len(data["assets"]) > 0 else ""
            asset_type = data["assets"][0].type if len(data["assets"]) > 0 else ""
            has_market_price = (
                data["assets"][0].has_market_price if len(data["assets"]) > 0 else True
            )
            tipos_ativos.add(asset_type)  # Adicionar o tipo ao conjunto

            # Calcular preço médio ponderado
            avg_price = (
                total_investment / data["quantity"] if data["quantity"] > 0 else 0
            )

            # Para ativos de renda fixa, buscar valores atualizados se existirem
            current_price = None
            price_variation = None
            price_variation_value = None

            if not has_market_price:
                # Buscar o ativo original para acessar os métodos
                original_asset = next(
                    (a for a in data["assets"] if a.ticker == normalized_ticker), None
                )

                if original_asset:
                    # Se tiver rendimento calculado
                    yield_info = original_asset.calculate_yield()
                    if yield_info:
                        current_price = (
                            yield_info["current_value"] / data["quantity"]
                            if data["quantity"] > 0
                            else 0
                        )
                        price_variation = yield_info["percentage_yield"]
                        price_variation_value = yield_info["absolute_yield"]

            portfolio_data.append(
                {
                    "ticker": normalized_ticker,
                    "name": name,
                    "type": asset_type,
                    "quantity": data["quantity"],
                    "avg_price": avg_price,
                    "total_value": total_investment,
                    "has_market_price": has_market_price,
                    "current_price": current_price,
                    "price_variation": price_variation,
                    "price_variation_value": price_variation_value,
                }
            )

    # Coletar tickers para buscar preços para uso no JavaScript
    tickers_to_check = []
    has_market_price_map = {}

    for asset_item in portfolio_data:
        ticker = asset_item["ticker"]
        has_market_price = asset_item["has_market_price"]

        # Verificar se o ticker é válido para consulta
        if ticker and has_market_price:
            tickers_to_check.append(ticker)
            has_market_price_map[ticker] = True

    # Calcular porcentagem de cada ativo na carteira
    for asset in portfolio_data:
        if total_value > 0:
            asset["percentage"] = (asset["total_value"] / total_value) * 100
        else:
            asset["percentage"] = 0

    # Converter o conjunto de tipos para uma lista ordenada
    tipos_ativos = sorted(list(tipos_ativos))

    return render_template(
        "index.html",
        portfolio=portfolio_data,
        total_value=total_value,
        total_current_value=total_value,  # Inicialmente igual ao valor de custo
        total_variation_value=0,  # Será atualizado via JavaScript
        total_variation_percent=0,  # Será atualizado via JavaScript
        tipos_ativos=tipos_ativos,
        market_tickers=tickers_to_check,  # Novos parâmetros para uso no JavaScript
    )


# Rota para visualizar o dashboard
@app.route("/dashboard")
def dashboard():
    assets = Asset.query.all()

    # Agrupar ativos pelo ticker normalizado
    assets_by_ticker = {}
    asset_types = {}
    tipos_ativos = set()  # Conjunto para armazenar os tipos únicos de ativos

    for asset in assets:
        normalized_ticker = normalize_ticker(asset.ticker)

        # Se o ticker não existe no dicionário, cria uma entrada nova
        if normalized_ticker not in assets_by_ticker:
            assets_by_ticker[normalized_ticker] = {
                "assets": [],
                "quantity": 0,
                "total_investment": 0,
                "name": asset.name,
                "type": asset.type,
                "sector": asset.sector,
            }

        # Adiciona o asset ao grupo
        assets_by_ticker[normalized_ticker]["assets"].append(asset)

        # Acumula quantidade e valor
        quantity = asset.current_quantity()
        if quantity > 0:
            avg_price = asset.calculate_average_price()
            asset_value = quantity * avg_price

            assets_by_ticker[normalized_ticker]["quantity"] += quantity
            assets_by_ticker[normalized_ticker]["total_investment"] += asset_value

            # Agrupar por tipo de ativo
            asset_type = asset.type
            tipos_ativos.add(asset_type)  # Adicionar o tipo ao conjunto
            if asset_type not in asset_types:
                asset_types[asset_type] = 0
            asset_types[asset_type] += asset_value

    # Constrói a lista de portfolio agrupada
    portfolio_data = []
    total_value = 0
    total_current_value = 0

    for normalized_ticker, data in assets_by_ticker.items():
        if data["quantity"] > 0:
            # Valores investidos por ativo
            total_investment = data["total_investment"]
            total_value += total_investment

            # Usar o nome do primeiro ativo no grupo (geralmente serão iguais)
            name = data["assets"][0].name if len(data["assets"]) > 0 else ""
            asset_type = data["assets"][0].type if len(data["assets"]) > 0 else ""
            sector = data["assets"][0].sector if len(data["assets"]) > 0 else ""
            has_market_price = (
                data["assets"][0].has_market_price if len(data["assets"]) > 0 else True
            )

            # Calcular preço médio ponderado
            avg_price = (
                total_investment / data["quantity"] if data["quantity"] > 0 else 0
            )

            # Para ativos de renda fixa, buscar valores atualizados se existirem
            current_price = None
            price_variation = None
            price_variation_value = None

            if not has_market_price:
                # Buscar o ativo original para acessar os métodos
                original_asset = next(
                    (a for a in data["assets"] if a.ticker == normalized_ticker), None
                )

                if original_asset:
                    # Se tiver rendimento calculado
                    yield_info = original_asset.calculate_yield()
                    if yield_info:
                        current_price = (
                            yield_info["current_value"] / data["quantity"]
                            if data["quantity"] > 0
                            else 0
                        )
                        price_variation = yield_info["percentage_yield"]
                        price_variation_value = yield_info["absolute_yield"]
                        total_current_value += yield_info["current_value"]
            else:
                # Para ativos de mercado, o valor atual será atualizado via JavaScript
                total_current_value += total_investment

            # Criar item para o portfolio
            portfolio_item = {
                "ticker": normalized_ticker,
                "name": name,
                "type": asset_type,
                "sector": sector,
                "quantity": data["quantity"],
                "avg_price": avg_price,
                "total_value": total_investment,
                "has_market_price": has_market_price,
                "current_price": current_price,
                "price_variation": price_variation,
                "price_variation_value": price_variation_value,
            }

            portfolio_data.append(portfolio_item)

    # Transformar os tipos de ativos em dados para o gráfico
    type_distribution = [
        {
            "type": k,
            "value": v,
            "percentage": (v / total_value * 100 if total_value > 0 else 0),
        }
        for k, v in asset_types.items()
    ]

    # Converter o conjunto de tipos para uma lista ordenada
    tipos_ativos = sorted(list(tipos_ativos))

    # Coletando tickers para buscar preços para uso no JavaScript
    tickers_to_check = []
    has_market_price_map = {}

    for asset_item in portfolio_data:
        ticker = asset_item["ticker"]
        has_market_price = asset_item["has_market_price"]

        # Verificar se o ticker é válido para consulta
        if ticker and has_market_price:
            tickers_to_check.append(ticker)
            has_market_price_map[ticker] = True

    # Calcular porcentagem de cada ativo na carteira
    for asset_item in portfolio_data:
        if total_value > 0:
            asset_item["percentage"] = (asset_item["total_value"] / total_value) * 100
        else:
            asset_item["percentage"] = 0

    return render_template(
        "dashboard.html",
        portfolio=portfolio_data,
        total_value=total_value,
        total_current_value=total_current_value,
        total_variation_value=total_current_value - total_value,
        total_variation_percent=(
            (total_current_value - total_value) / total_value * 100
            if total_value > 0
            else 0
        ),
        type_distribution=type_distribution,
        tipos_ativos=tipos_ativos,
        market_tickers=tickers_to_check,
    )


# Rotas para Assets (Ativos)
@app.route("/assets")
def list_assets():
    assets = Asset.query.all()
    return render_template("assets/list.html", assets=assets)


@app.route("/assets/new", methods=["GET", "POST"])
def new_asset():
    if request.method == "POST":
        # Determinar o tipo de ativo (padrão ou personalizado)
        asset_type = request.form["type"]
        if asset_type == "custom" and "customType" in request.form:
            asset_type = request.form["customType"]

        # Determinar o setor (padrão, personalizado ou nenhum)
        sector = request.form["sector"]
        if sector == "custom" and "customSector" in request.form:
            sector = request.form["customSector"]

        # Verificar se é um ativo com ticker de mercado ou renda fixa
        has_market_price = request.form.get("ticker_type") == "market"

        if has_market_price:
            # Ativo com ticker de mercado (ações, FIIs, etc.)
            ticker = request.form["ticker"].upper()
            name = request.form["name"]
            issuer = None
            maturity_date = None
        else:
            # Ativo de renda fixa sem ticker (LCA, CDB, etc.)
            fixed_income_type = request.form.get("fixed_income_type")
            issuer = request.form.get("issuer")
            name = request.form.get("fixed_income_name")

            # Gerar um ticker interno para o ativo de renda fixa
            ticker = Asset.generate_ticker_for_fixed_income(fixed_income_type, issuer)

            # Tratar data de vencimento, se fornecida
            maturity_date_str = request.form.get("maturity_date")
            maturity_date = None
            if maturity_date_str:
                try:
                    maturity_date = datetime.strptime(
                        maturity_date_str, "%Y-%m-%d"
                    ).date()
                except:
                    pass

        # Criar o ativo
        asset = Asset(
            ticker=ticker,
            name=name,
            type=asset_type,
            sector=sector,
            has_market_price=has_market_price,
            issuer=issuer,
            maturity_date=maturity_date,
        )
        db.session.add(asset)
        db.session.commit()

        # Se for um ativo de renda fixa, criar automaticamente uma transação de compra
        if (
            not has_market_price
            and "investment_value" in request.form
            and request.form["investment_value"]
        ):
            try:
                # Obter dados do investimento
                investment_value = float(request.form["investment_value"])
                investment_date_str = request.form.get("investment_date")
                investment_date = datetime.now().date()
                if investment_date_str:
                    try:
                        investment_date = datetime.strptime(
                            investment_date_str, "%Y-%m-%d"
                        ).date()
                    except:
                        pass

                # Quantidade padrão é 1 para renda fixa, mas pode ser alterada
                investment_quantity = 1
                if (
                    "investment_quantity" in request.form
                    and request.form["investment_quantity"]
                ):
                    try:
                        investment_quantity = int(request.form["investment_quantity"])
                    except:
                        pass

                # Calcular o preço unitário (valor total / quantidade)
                unit_price = investment_value
                if investment_quantity > 0:
                    unit_price = investment_value / investment_quantity

                # Criar a transação
                transaction = Transaction(
                    asset_id=asset.id,
                    date=investment_date,
                    operation_type="compra",
                    quantity=investment_quantity,
                    price=unit_price,
                    total_value=investment_value,
                    taxes=0,
                    notes=request.form.get("investment_notes", ""),
                )
                db.session.add(transaction)
                db.session.commit()

                flash("Ativo e investimento registrados com sucesso!", "success")
            except Exception as e:
                flash(
                    f"Ativo criado, mas houve um erro ao registrar o investimento: {str(e)}",
                    "warning",
                )
        else:
            flash("Ativo adicionado com sucesso!", "success")

        return redirect(url_for("list_assets"))

    # Obter todos os tipos de ativos e setores distintos do banco de dados
    asset_types_default = [
        "Ação",
        "FII",
        "ETF",
        "BDR",
        "Tesouro Direto",
        "CDB",
        "LCI",
        "LCA",
        "Debênture",
        "Outro",
    ]
    sectors_default = [
        "Financeiro",
        "Energia",
        "Tecnologia",
        "Consumo",
        "Saúde",
        "Industrial",
        "Imobiliário",
        "Commodities",
        "Utilidades",
        "Telecomunicações",
        "Outros",
    ]

    # Consultar tipos de ativos distintos no banco de dados
    db_asset_types = db.session.query(Asset.type).distinct().all()
    db_asset_types = [t[0] for t in db_asset_types if t[0] not in asset_types_default]

    # Consultar setores distintos no banco de dados
    db_sectors = db.session.query(Asset.sector).distinct().all()
    db_sectors = [s[0] for s in db_sectors if s[0] and s[0] not in sectors_default]

    # Passar a data atual para o template
    today_date = datetime.now().strftime("%Y-%m-%d")

    return render_template(
        "assets/form.html",
        db_asset_types=db_asset_types,
        db_sectors=db_sectors,
        today_date=today_date,
    )


@app.route("/assets/<int:id>/edit", methods=["GET", "POST"])
def edit_asset(id):
    asset = Asset.query.get_or_404(id)
    if request.method == "POST":
        # Determinar o tipo de ativo (padrão ou personalizado)
        asset_type = request.form["type"]
        if asset_type == "custom" and "customType" in request.form:
            asset_type = request.form["customType"]

        # Determinar o setor (padrão, personalizado ou nenhum)
        sector = request.form["sector"]
        if sector == "custom" and "customSector" in request.form:
            sector = request.form["customSector"]

        # Verificar se é um ativo com ticker de mercado ou renda fixa
        new_has_market_price = request.form.get("ticker_type") == "market"
        asset.ticker = request.form["ticker"].upper()
        asset.name = request.form["name"]
        asset.type = asset_type
        asset.sector = sector

        # Se mudou de tipo de ticker, pode precisar gerar um novo identificador
        if new_has_market_price != asset.has_market_price:
            asset.has_market_price = new_has_market_price
            if new_has_market_price:
                # Mudou para ativo de mercado
                asset.ticker = request.form["ticker"].upper()
            else:
                # Mudou para ativo de renda fixa
                new_fixed_income_type = request.form.get("fixed_income_type")
                new_issuer = request.form.get("issuer")
                if new_fixed_income_type != asset.type or new_issuer != asset.issuer:
                    asset.ticker = Asset.generate_ticker_for_fixed_income(
                        new_fixed_income_type, new_issuer
                    )
                asset.type = new_fixed_income_type
                asset.issuer = new_issuer

                # Tratar data de vencimento, se fornecida
                maturity_date_str = request.form.get("maturity_date")
                if maturity_date_str:
                    try:
                        asset.maturity_date = datetime.strptime(
                            maturity_date_str, "%Y-%m-%d"
                        ).date()
                    except:
                        pass

        db.session.commit()
        flash("Ativo atualizado com sucesso!", "success")
        return redirect(url_for("list_assets"))

    # Obter todos os tipos de ativos e setores distintos do banco de dados
    asset_types_default = [
        "Ação",
        "FII",
        "ETF",
        "BDR",
        "Tesouro Direto",
        "CDB",
        "LCI",
        "LCA",
        "Debênture",
        "Outro",
    ]
    sectors_default = [
        "Financeiro",
        "Energia",
        "Tecnologia",
        "Consumo",
        "Saúde",
        "Industrial",
        "Imobiliário",
        "Commodities",
        "Utilidades",
        "Telecomunicações",
        "Outros",
    ]

    # Consultar tipos de ativos distintos no banco de dados
    db_asset_types = db.session.query(Asset.type).distinct().all()
    db_asset_types = [t[0] for t in db_asset_types if t[0] not in asset_types_default]

    # Consultar setores distintos no banco de dados
    db_sectors = db.session.query(Asset.sector).distinct().all()
    db_sectors = [s[0] for s in db_sectors if s[0] and s[0] not in sectors_default]

    # Passar a data atual para o template
    today_date = datetime.now().strftime("%Y-%m-%d")

    return render_template(
        "assets/form.html",
        asset=asset,
        db_asset_types=db_asset_types,
        db_sectors=db_sectors,
        today_date=today_date,
    )


@app.route("/assets/<int:id>/delete", methods=["POST"])
def delete_asset(id):
    asset = Asset.query.get_or_404(id)
    db.session.delete(asset)
    db.session.commit()
    flash("Ativo excluído com sucesso!", "success")
    return redirect(url_for("list_assets"))


# Rotas para Transactions (Transações)
@app.route("/transactions")
def list_transactions():
    transactions = Transaction.query.order_by(Transaction.date.desc()).all()
    return render_template("transactions/list.html", transactions=transactions)


@app.route("/transactions/new", methods=["GET", "POST"])
def new_transaction():
    assets = Asset.query.all()
    if request.method == "POST":
        asset_id = request.form["asset_id"]
        quantity = int(request.form["quantity"])
        price = float(request.form["price"])

        transaction = Transaction(
            asset_id=asset_id,
            date=datetime.strptime(request.form["date"], "%Y-%m-%d").date(),
            operation_type=request.form["operation_type"],
            quantity=quantity,
            price=price,
            total_value=quantity * price,
            taxes=float(request.form["taxes"]) if request.form["taxes"] else 0,
            notes=request.form["notes"],
        )
        db.session.add(transaction)
        db.session.commit()
        flash("Transação registrada com sucesso!", "success")
        return redirect(url_for("list_transactions"))
    return render_template("transactions/form.html", assets=assets)


@app.route("/transactions/<int:id>/edit", methods=["GET", "POST"])
def edit_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    assets = Asset.query.all()
    if request.method == "POST":
        transaction.asset_id = request.form["asset_id"]
        transaction.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        transaction.operation_type = request.form["operation_type"]
        transaction.quantity = int(request.form["quantity"])
        transaction.price = float(request.form["price"])
        transaction.total_value = transaction.quantity * transaction.price
        transaction.taxes = float(request.form["taxes"]) if request.form["taxes"] else 0
        transaction.notes = request.form["notes"]
        db.session.commit()
        flash("Transação atualizada com sucesso!", "success")
        return redirect(url_for("list_transactions"))
    return render_template(
        "transactions/form.html", transaction=transaction, assets=assets
    )


@app.route("/transactions/<int:id>/delete", methods=["POST"])
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    db.session.delete(transaction)
    db.session.commit()
    flash("Transação excluída com sucesso!", "success")
    return redirect(url_for("list_transactions"))


# Rota para importação de dados da B3
@app.route("/import_b3", methods=["GET", "POST"])
def import_b3():
    if request.method == "POST":
        if "file" not in request.files:
            flash("Nenhum arquivo selecionado", "error")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("Nenhum arquivo selecionado", "error")
            return redirect(request.url)

        if file and file.filename.endswith((".xlsx", ".xls")):
            try:
                # Salvar o arquivo temporariamente
                file_path = os.path.join(app.root_path, "temp", file.filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)

                # Tentar ler o arquivo Excel
                try:
                    df = pd.read_excel(file_path)
                    print("Colunas encontradas no arquivo:", df.columns.tolist())
                except Exception as e:
                    flash(f"Erro ao ler o arquivo Excel: {str(e)}", "error")
                    return redirect(request.url)

                # Detectar o formato do arquivo automaticamente
                # Novo formato com as colunas: Data do Negócio, Tipo de Movimentação, Código de Negociação, Quantidade, Preço, Valor
                format_type = "unknown"

                # Verificar se é o novo formato
                new_format_columns = [
                    "Data do Negócio",
                    "Tipo de Movimentação",
                    "Código de Negociação",
                    "Quantidade",
                    "Preço",
                    "Valor",
                ]
                if all(col in df.columns for col in new_format_columns):
                    format_type = "new"
                    print("Formato novo detectado!")

                # Verificar se é o formato antigo
                old_format_columns = [
                    "Código",
                    "Quantidade",
                    "Preço (R$)",
                    "Data",
                    "Compra/Venda",
                    "Valor (R$)",
                ]
                if all(col in df.columns for col in old_format_columns):
                    format_type = "old"
                    print("Formato antigo detectado!")

                if format_type == "unknown":
                    missing_new = [
                        col for col in new_format_columns if col not in df.columns
                    ]
                    missing_old = [
                        col for col in old_format_columns if col not in df.columns
                    ]
                    flash(
                        f'Formato de arquivo não reconhecido. Colunas necessárias não encontradas. Faltando: {", ".join(missing_new)}',
                        "error",
                    )
                    return redirect(request.url)

                # Contadores para feedback
                transactions_added = 0
                assets_added = 0

                # Processar cada linha de negociação
                for index, row in df.iterrows():
                    try:
                        if format_type == "new":
                            # Processar no formato novo
                            # Ignorar linhas sem código de ativo
                            if pd.isna(row["Código de Negociação"]) or not isinstance(
                                row["Código de Negociação"], str
                            ):
                                continue
                            ticker = row["Código de Negociação"].strip()

                            # Tratamento para quantidade
                            try:
                                quantity = int(row["Quantidade"])
                            except (ValueError, TypeError):
                                quantity = 0
                                continue  # Pular esta linha se não for possível converter a quantidade

                            # Tratamento para preço
                            try:
                                price_value = row["Preço"]
                                if isinstance(price_value, str):
                                    price_value = price_value.replace(".", "").replace(
                                        ",", "."
                                    )
                                price = float(price_value)
                            except (ValueError, TypeError):
                                continue  # Pular esta linha se não for possível converter o preço

                            # Tratamento para data
                            try:
                                if isinstance(row["Data do Negócio"], str):
                                    operation_date = datetime.strptime(
                                        row["Data do Negócio"], "%d/%m/%Y"
                                    ).date()
                                else:
                                    operation_date = (
                                        row["Data do Negócio"].date()
                                        if hasattr(row["Data do Negócio"], "date")
                                        else row["Data do Negócio"]
                                    )
                            except (ValueError, TypeError, AttributeError):
                                operation_date = datetime.now().date()

                            # Tratamento para tipo de operação
                            # Compra ou venda baseado no campo "Tipo de Movimentação"
                            operation_type = "compra"
                            if "Tipo de Movimentação" in row and isinstance(
                                row["Tipo de Movimentação"], str
                            ):
                                if any(
                                    term in row["Tipo de Movimentação"].lower()
                                    for term in ["venda", "vend", "saída", "saida"]
                                ):
                                    operation_type = "venda"

                            # Tratamento para valor total
                            try:
                                total_value = row["Valor"]
                                if isinstance(total_value, str):
                                    total_value = total_value.replace(".", "").replace(
                                        ",", "."
                                    )
                                total = float(total_value)
                            except (ValueError, TypeError):
                                total = quantity * price

                        elif format_type == "old":
                            # Processar no formato antigo
                            # Ignorar linhas sem ticker
                            if pd.isna(row["Código"]) or not isinstance(
                                row["Código"], str
                            ):
                                continue
                            ticker = row["Código"].strip()

                            # Tratamento para quantidade
                            try:
                                quantity = int(row["Quantidade"])
                            except (ValueError, TypeError):
                                quantity = 0
                                continue  # Pular esta linha se não for possível converter a quantidade

                            # Tratamento para preço
                            try:
                                price_value = row["Preço (R$)"]
                                if isinstance(price_value, str):
                                    price_value = price_value.replace(".", "").replace(
                                        ",", "."
                                    )
                                price = float(price_value)
                            except (ValueError, TypeError):
                                continue  # Pular esta linha se não for possível converter o preço

                            # Tratamento para data
                            try:
                                if isinstance(row["Data"], str):
                                    operation_date = datetime.strptime(
                                        row["Data"], "%d/%m/%Y"
                                    ).date()
                                else:
                                    operation_date = (
                                        row["Data"].date()
                                        if hasattr(row["Data"], "date")
                                        else row["Data"]
                                    )
                            except (ValueError, TypeError, AttributeError):
                                operation_date = datetime.now().date()

                            # Tratamento para tipo de operação
                            operation_type = (
                                "compra" if row["Compra/Venda"] == "C" else "venda"
                            )

                            # Tratamento para valor total
                            try:
                                total_value = row["Valor (R$)"]
                                if isinstance(total_value, str):
                                    total_value = total_value.replace(".", "").replace(
                                        ",", "."
                                    )
                                total = float(total_value)
                            except (ValueError, TypeError):
                                total = quantity * price

                        # Verificar se o ativo já existe, senão criar
                        asset = Asset.query.filter_by(ticker=ticker).first()
                        if not asset:
                            asset = Asset(
                                ticker=ticker,
                                name=ticker,  # Nome temporário, pode ser atualizado manualmente depois
                                type="Ação",  # Tipo padrão, pode ser atualizado manualmente depois
                                sector="Outros",  # Setor padrão, pode ser atualizado manualmente depois
                            )
                            db.session.add(asset)
                            db.session.commit()
                            assets_added += 1

                        # Criar a transação
                        transaction = Transaction(
                            asset_id=asset.id,
                            date=operation_date,
                            operation_type=operation_type,
                            quantity=quantity,
                            price=price,
                            total_value=total,
                            taxes=0,  # Taxas podem ser atualizadas manualmente depois
                        )
                        db.session.add(transaction)
                        transactions_added += 1
                        print(
                            f"Transação adicionada: {ticker}, {quantity}, {price}, {operation_date}, {operation_type}"
                        )
                    except Exception as row_error:
                        print(f"Erro ao processar linha {index}: {str(row_error)}")
                        continue  # Continuar para a próxima linha em caso de erro

                db.session.commit()

                # Remover o arquivo temporário
                if os.path.exists(file_path):
                    os.remove(file_path)

                if transactions_added > 0:
                    flash(
                        f"Importação concluída! {assets_added} novos ativos e {transactions_added} transações adicionadas.",
                        "success",
                    )
                    return redirect(url_for("list_transactions"))
                else:
                    flash(
                        "Nenhuma transação válida encontrada no arquivo. Verifique o formato.",
                        "warning",
                    )
                    return redirect(request.url)

            except Exception as e:
                error_msg = f"Erro ao processar o arquivo: {str(e)}"
                print(
                    error_msg
                )  # Imprimir o erro no console para ajudar no diagnóstico
                flash(error_msg, "error")
                return redirect(request.url)
        else:
            flash(
                "Formato de arquivo não suportado. Use arquivos .xlsx ou .xls", "error"
            )
            return redirect(request.url)

    return render_template("import_b3.html")


# Rota para atualizar o valor atual de um ativo de renda fixa
@app.route("/assets/<int:id>/update-value", methods=["GET", "POST"])
def update_asset_value(id):
    asset = Asset.query.get_or_404(id)

    # Verificar se o ativo é de renda fixa
    if asset.has_market_price:
        flash(
            "Apenas ativos de renda fixa podem ter o valor manualmente atualizado.",
            "warning",
        )
        return redirect(url_for("list_assets"))

    if request.method == "POST":
        try:
            # Obter dados do formulário
            current_value = float(request.form["current_value"])
            date_str = request.form["date"]
            date = datetime.now().date()
            if date_str:
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except:
                    pass

            notes = request.form.get("notes", "")

            # Criar nova atualização de valor
            value_update = AssetValueUpdate(
                asset_id=asset.id, date=date, current_value=current_value, notes=notes
            )

            db.session.add(value_update)
            db.session.commit()

            flash("Valor do investimento atualizado com sucesso!", "success")
            return redirect(url_for("list_assets"))
        except Exception as e:
            flash(f"Erro ao atualizar valor: {str(e)}", "danger")

    # Preparar dados para o template
    valor_investido = asset.calculate_average_price() * asset.current_quantity()

    # Obter a atualização de valor mais recente, se existir
    ultimo_valor = (
        AssetValueUpdate.query.filter_by(asset_id=asset.id)
        .order_by(AssetValueUpdate.date.desc())
        .first()
    )

    # Passar a data atual para o template
    today_date = datetime.now().strftime("%Y-%m-%d")

    return render_template(
        "assets/update_value.html",
        asset=asset,
        valor_investido=valor_investido,
        ultimo_valor=ultimo_valor,
        today_date=today_date,
    )


# Rota API para obter preços atuais
@app.route("/api/prices", methods=["POST"])
def api_get_prices():
    """
    API para buscar preços de ativos.

    Recebe um JSON com a lista de tickers e um mapa opcional de tickers que têm preço de mercado.
    Retorna um JSON com os preços dos ativos.
    """
    try:
        # Obter dados da requisição
        data = request.get_json()
        logger.info(f"API /api/prices - Requisição recebida: {data}")

        if not data or "tickers" not in data:
            logger.warning(
                "API /api/prices - Parâmetros inválidos: 'tickers' não fornecidos"
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Parâmetros inválidos",
                        "message": "A lista de tickers é obrigatória",
                    }
                ),
                400,
            )

        tickers = data.get("tickers", [])
        has_market_price_map = data.get("hasMarketPriceMap", {})

        # Validar a lista de tickers
        if not tickers or not isinstance(tickers, list):
            logger.warning("API /api/prices - Lista de tickers inválida")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Parâmetros inválidos",
                        "message": "A lista de tickers deve ser um array não vazio",
                    }
                ),
                400,
            )

        # Log para diagnóstico
        logger.info(
            f"API /api/prices - Recebido pedido de preços para {len(tickers)} tickers: {tickers}"
        )
        if has_market_price_map:
            logger.info(
                f"API /api/prices - has_market_price_map: {has_market_price_map}"
            )

        # Filtragem de tickers vazios ou inválidos
        tickers = [t for t in tickers if t and isinstance(t, str)]
        logger.info(f"API /api/prices - Após filtragem: {len(tickers)} tickers válidos")

        # Buscar preços
        if tickers:
            from app.services.price_service import get_asset_prices

            # Tentativa adicional para garantir que o mapa de has_market_price está correto
            # Converter strings para valores booleanos
            clean_market_price_map = {}
            for ticker, value in has_market_price_map.items():
                if isinstance(value, str):
                    clean_market_price_map[ticker] = value.lower() in (
                        "true",
                        "1",
                        "yes",
                    )
                else:
                    clean_market_price_map[ticker] = bool(value)

            logger.info(
                f"API /api/prices - Mapa de has_market_price limpo: {clean_market_price_map}"
            )

            # Buscar preços com o service
            prices_data = get_asset_prices(tickers, clean_market_price_map)
            logger.info(
                f"API /api/prices - Preços retornados pelo service: {prices_data}"
            )

            # Formatar dados de retorno para garantir consistência
            formatted_prices = {}
            for ticker, price in prices_data.items():
                if ticker and price is not None:
                    if isinstance(price, (int, float)) and not isinstance(price, bool):
                        formatted_prices[ticker] = {"price": float(price)}
                    elif isinstance(price, dict) and "price" in price:
                        formatted_prices[ticker] = {"price": float(price["price"])}

            logger.info(f"API /api/prices - Preços formatados: {formatted_prices}")
            return jsonify({"success": True, "prices": formatted_prices})
        else:
            logger.warning("API /api/prices - Nenhum ticker válido após filtragem")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Sem tickers válidos",
                        "message": "Nenhum ticker válido para buscar preços",
                    }
                ),
                400,
            )

    except Exception as e:
        logger.error(f"API /api/prices - Erro ao buscar preços: {str(e)}")
        import traceback

        logger.error(f"API /api/prices - Traceback: {traceback.format_exc()}")
        return (
            jsonify({"success": False, "error": "Erro interno", "message": str(e)}),
            500,
        )
