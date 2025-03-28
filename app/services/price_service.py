import requests
import yfinance as yf
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from functools import lru_cache
import traceback

# Configurar logging mais detalhado
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Adicionar handler para console para garantir que os logs sejam visíveis
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)


# Cache para armazenar preços por 15 minutos (evita muitas requisições à API)
@lru_cache(maxsize=128)
def get_current_prices(tickers, timestamp=None):
    """
    Busca os preços atuais dos ativos usando a API do Yahoo Finance.

    Args:
        tickers: Lista de tickers para buscar preços
        timestamp: Timestamp usado para cache (atualiza a cada 15 minutos)

    Returns:
        Dictionary com ticker -> preço
    """
    logger.info(f"=== INICIANDO BUSCA DE PREÇOS (TIMESTAMP: {timestamp}) ===")
    logger.info(f"Tickers recebidos no get_current_prices: {tickers}")
    
    # Se timestamp não for fornecido, cria um com base no tempo atual (arredondado para 15 minutos)
    if timestamp is None:
        now = datetime.now()
        timestamp = now.replace(
            minute=now.minute - now.minute % 15, second=0, microsecond=0
        )
        logger.info(f"Timestamp criado: {timestamp}")

    # Dictionary para armazenar resultados
    prices = {}

    # Preparar tickers para o formato do Yahoo Finance (adicionar .SA para ativos brasileiros)
    yf_tickers = []
    ticker_mapping = {}  # Mapear de ticker YF para ticker original

    for ticker in tickers:
        if not ticker:  # Ignorar tickers vazios
            logger.warning(f"Ticker vazio ignorado")
            continue

        # Para tickers brasileiros, não adicionar o sufixo .SA (já estamos consultando direto)
        yf_ticker = ticker

        # Remover espaços ou caracteres especiais
        yf_ticker = yf_ticker.strip().replace(" ", "")

        yf_tickers.append(yf_ticker)
        ticker_mapping[yf_ticker] = ticker
        logger.info(f"Ticker formatado: {ticker} -> {yf_ticker}")

    # Log dos tickers que estamos buscando
    logger.info(f"Buscando preços para {len(yf_tickers)} tickers: {yf_tickers}")

    try:
        if not yf_tickers:  # Se não há tickers para buscar, retorna um dicionário vazio
            logger.info("Nenhum ticker para buscar")
            return prices

        # Método 1: Tentar usar yfinance.download sem .SA
        logger.info("=== MÉTODO 1: yfinance.download sem .SA ===")
        try:
            # Buscar dados para todos os tickers de uma vez (mais eficiente)
            logger.info(f"Executando yf.download para {len(yf_tickers)} tickers")
            data = yf.download(yf_tickers, period="1d", progress=False)
            logger.info(f"Resposta do yfinance.download: {data.shape if not data.empty else 'vazio'}")
            
            if not data.empty:
                logger.info(f"Colunas disponíveis: {data.columns}")
            
            # Se só tem um ticker, o formato é diferente
            if len(yf_tickers) == 1:
                logger.info("Processando resposta para um único ticker")
                if not data.empty and "Close" in data.columns:
                    price = data["Close"].iloc[-1]
                    if not np.isnan(price):
                        prices[ticker_mapping[yf_tickers[0]]] = price
                        logger.info(f"Preço encontrado para {yf_tickers[0]}: {price}")
                    else:
                        logger.warning(f"Preço NaN para {yf_tickers[0]}")
                else:
                    logger.warning(f"Dados não encontrados para {yf_tickers[0]}")
            else:
                # Para múltiplos tickers
                logger.info("Processando resposta para múltiplos tickers")
                for yf_ticker in yf_tickers:
                    try:
                        if not data.empty and ("Close", yf_ticker) in data.columns:
                            price = data[("Close", yf_ticker)].iloc[-1]
                            if not np.isnan(price):
                                prices[ticker_mapping[yf_ticker]] = price
                                logger.info(f"Preço encontrado para {yf_ticker}: {price}")
                            else:
                                logger.warning(f"Preço NaN para {yf_ticker}")
                        else:
                            logger.warning(f"Dados não encontrados para {yf_ticker} no resultado combinado")
                    except Exception as e:
                        logger.error(f"Erro ao processar ticker {yf_ticker}: {str(e)}")
                        logger.error(traceback.format_exc())
        except Exception as e:
            logger.error(f"Erro no método 1 (yfinance.download): {str(e)}")
            logger.error(traceback.format_exc())

        # Método 2: Se o método 1 falhar, tentar com .SA para tickers brasileiros
        missing_tickers = [t for t in tickers if t not in prices]
        if missing_tickers:
            logger.info(f"=== MÉTODO 2: Ticker individual com .SA ===")
            logger.info(f"Tickers não encontrados pelo método 1: {missing_tickers} ({len(missing_tickers)} de {len(tickers)})")
            
            for ticker in missing_tickers:
                try:
                    # Adicionar .SA para tentar novamente
                    yf_ticker_format = f"{ticker}.SA"
                    logger.info(f"Tentando ticker {ticker} com formato {yf_ticker_format}")
                    t = yf.Ticker(yf_ticker_format)
                    
                    # Obter dados de hoje
                    hist = t.history(period="1d")
                    logger.info(f"Histórico obtido para {yf_ticker_format}: {hist.shape if not hist.empty else 'vazio'}")
                    
                    if not hist.empty and "Close" in hist.columns:
                        price = hist["Close"].iloc[-1]
                        if not np.isnan(price):
                            prices[ticker] = price
                            logger.info(f"Método 2: Preço encontrado para {ticker}: {price}")
                        else:
                            logger.warning(f"Método 2: Preço NaN para {ticker}")
                    else:
                        logger.warning(f"Método 2: Sem histórico para {ticker}")
                        
                    # Se ainda não tem preço, tentar info
                    if ticker not in prices:
                        logger.info(f"Tentando obter info para {yf_ticker_format}")
                        info = t.info
                        if 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
                            price = info['regularMarketPrice']
                            prices[ticker] = price
                            logger.info(f"Método 2 (info): Preço encontrado para {ticker}: {price}")
                        else:
                            logger.warning(f"Método 2 (info): Preço não disponível para {ticker}")
                        
                except Exception as e:
                    logger.error(f"Método 2: Erro ao processar ticker {ticker}: {str(e)}")
                    logger.error(traceback.format_exc())

        # Método 3: Tentar individualmente sem .SA para tickers que não foram encontrados
        missing_tickers = [t for t in tickers if t not in prices]
        if missing_tickers:
            logger.info(f"=== MÉTODO 3: Ticker individual sem .SA ===")
            logger.info(f"Tickers não encontrados pelos métodos anteriores: {missing_tickers} ({len(missing_tickers)} de {len(tickers)})")
            
            for ticker in missing_tickers:
                try:
                    logger.info(f"Tentando ticker {ticker} diretamente")
                    t = yf.Ticker(ticker)  # Sem .SA
                    hist = t.history(period="1d")
                    logger.info(f"Histórico obtido para {ticker}: {hist.shape if not hist.empty else 'vazio'}")
                    
                    if not hist.empty and "Close" in hist.columns:
                        price = hist["Close"].iloc[-1]
                        if not np.isnan(price):
                            prices[ticker] = price
                            logger.info(f"Método 3: Preço encontrado para {ticker}: {price}")
                        else:
                            logger.warning(f"Método 3: Preço NaN para {ticker}")
                    else:
                        logger.warning(f"Método 3: Sem histórico para {ticker}")
                        
                    # Se ainda não tem preço, tentar info
                    if ticker not in prices:
                        logger.info(f"Tentando obter info para {ticker}")
                        info = t.info
                        if 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
                            price = info['regularMarketPrice']
                            prices[ticker] = price
                            logger.info(f"Método 3 (info): Preço encontrado para {ticker}: {price}")
                        else:
                            logger.warning(f"Método 3 (info): Preço não disponível para {ticker}")
                        
                except Exception as e:
                    logger.error(f"Método 3: Erro ao processar ticker {ticker}: {str(e)}")
                    logger.error(traceback.format_exc())

        # Método 4: Alternativa usando API Alpha Vantage (se configurada)
        # Este método poderia ser implementado como alternativa ao Yahoo Finance

    except Exception as e:
        logger.error(f"Erro geral ao buscar preços: {str(e)}")
        logger.error(traceback.format_exc())

    # Garantir que todos os preços são números
    for ticker, price in list(prices.items()):
        try:
            prices[ticker] = float(price)
        except (ValueError, TypeError):
            logger.error(f"Valor de preço inválido para {ticker}: {price}")
            del prices[ticker]

    logger.info(f"=== RESULTADO FINAL: {len(prices)} de {len(tickers)} preços encontrados ===")
    for ticker, price in prices.items():
        logger.info(f"Ticker {ticker}: R$ {price}")
    
    return prices


# Função simplificada para uso no aplicativo
def get_asset_prices(tickers, has_market_price_map=None):
    """
    Função de uso mais simples que gerencia o cache interno.
    
    Args:
        tickers: Lista de tickers para buscar preços
        has_market_price_map: Dicionário mapeando tickers para flag has_market_price
    
    Returns:
        Dictionary com ticker -> preço
    """
    logger.info(f"=== INICIANDO GET_ASSET_PRICES ===")
    # Filtrar tickers vazios ou None e tickers de ativos que não têm preço de mercado
    valid_tickers = []
    
    # Log para diagnóstico
    logger.info(f"Tickers recebidos ({len(tickers)}): {tickers}")
    if has_market_price_map:
        logger.info(f"has_market_price_map: {has_market_price_map}")
    
    # Verificar e limpar o mapa de has_market_price
    clean_market_price_map = {}
    if has_market_price_map:
        for ticker, value in has_market_price_map.items():
            if isinstance(value, str):
                clean_market_price_map[ticker] = value.lower() in ('true', '1', 'yes')
            else:
                clean_market_price_map[ticker] = bool(value)
        logger.info(f"has_market_price_map limpo: {clean_market_price_map}")
    
    # Filtrar tickers com base no mapa de has_market_price
    if clean_market_price_map:
        # Usar apenas tickers que têm has_market_price=True
        valid_tickers = [t for t in tickers if t and clean_market_price_map.get(t, True)]
        logger.info(f"Tickers filtrados por has_market_price: {valid_tickers}")
    else:
        # Se não tiver o mapa, usar todos os tickers exceto formatos de renda fixa
        valid_tickers = [t for t in tickers if t]
        valid_tickers = [t for t in valid_tickers if '-' not in t]
        logger.info(f"Tickers filtrados (sem mapa): {valid_tickers}")

    logger.info(f"Tickers válidos após filtragem: {valid_tickers} ({len(valid_tickers)} de {len(tickers)})")
    
    if not valid_tickers:
        logger.warning("Nenhum ticker válido para buscar preços")
        return {}

    # Criar timestamp que atualiza a cada 15 minutos para uso com cache
    now = datetime.now()
    cache_timestamp = now.replace(
        minute=now.minute - now.minute % 15, second=0, microsecond=0
    )
    logger.info(f"Timestamp para cache: {cache_timestamp}")

    logger.info(f"Buscando preços para {len(valid_tickers)} tickers válidos")
    try:
        # Buscar preços com cache - convertendo para tupla para funcionar com lru_cache
        result = get_current_prices(tuple(set(valid_tickers)), cache_timestamp)
        logger.info(f"Retornando {len(result)} preços")
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar preços: {str(e)}")
        logger.error(traceback.format_exc())
        return {}


# Função para buscar preços de tickers específicos
def get_ticker_price(ticker):
    """
    Função para buscar o preço de um único ticker.

    Args:
        ticker: Ticker para buscar o preço

    Returns:
        Preço atual ou None se não encontrado
    """
    logger.info(f"Buscando preço para ticker individual: {ticker}")
    if not ticker:
        logger.warning("Ticker vazio, retornando None")
        return None

    try:
        prices = get_asset_prices([ticker])
        price = prices.get(ticker)
        logger.info(f"Preço encontrado para {ticker}: {price}")
        return price
    except Exception as e:
        logger.error(f"Erro ao buscar preço para {ticker}: {str(e)}")
        logger.error(traceback.format_exc())
        return None
