// Função para atualizar preços dos ativos via API
document.addEventListener('DOMContentLoaded', function() {
    console.log('=== INICIALIZANDO SISTEMA DE PREÇOS ===');
    
    // Obter os tickers do elemento oculto no HTML
    const marketTickersElement = document.getElementById('market-tickers');
    if (!marketTickersElement) {
        console.log('Elemento market-tickers não encontrado na página');
        return;
    }
    
    console.log('Elemento market-tickers encontrado:', marketTickersElement);
    
    try {
        // Tentar obter os tickers do atributo data-tickers
        let tickers = [];
        try {
            let tickersRaw = marketTickersElement.getAttribute('data-tickers');
            console.log('Dados brutos de tickers:', tickersRaw);
            
            if (tickersRaw && tickersRaw.trim() !== '' && tickersRaw !== '[]' && tickersRaw !== 'null') {
                try {
                    // Correção para JSON incompleto
                    if (tickersRaw.startsWith('[') && !tickersRaw.endsWith(']')) {
                        console.log('Detectado JSON incompleto, corrigindo...');
                        tickersRaw += ']';
                    }
                    
                    // Limpeza adicional para garantir JSON válido
                    tickersRaw = tickersRaw.replace(/'/g, '"').trim();
                    
                    // Verificação extra para garantir que temos um array válido
                    if (tickersRaw === '[') {
                        tickersRaw = '[]';
                    }
                    
                    console.log('JSON após limpeza:', tickersRaw);
                    
                    // Agora tenta fazer o parse do JSON corrigido
                    try {
                        tickers = JSON.parse(tickersRaw);
                        console.log('Tickers obtidos após correção:', tickers);
                    } catch (innerError) {
                        console.error('Ainda não foi possível fazer parse do JSON:', innerError);
                        console.log('Valor que causou o erro:', tickersRaw);
                        
                        // Última tentativa: extrair manualmente os tickers
                        if (tickersRaw.includes('"') || tickersRaw.includes("'")) {
                            // Tenta extrair qualquer coisa entre aspas
                            const matches = tickersRaw.match(/["']([^"']+)["']/g);
                            if (matches && matches.length > 0) {
                                tickers = matches.map(m => m.replace(/["']/g, ''));
                                console.log('Tickers extraídos manualmente:', tickers);
                            }
                        } else if (tickersRaw.includes(',')) {
                            // Tenta dividir por vírgulas se não houver aspas
                            tickers = tickersRaw.replace(/[\[\]]/g, '').split(',').map(t => t.trim()).filter(t => t);
                            console.log('Tickers extraídos por vírgulas:', tickers);
                        }
                    }
                } catch (jsonError) {
                    console.error('Erro ao fazer parse do JSON de tickers:', jsonError);
                    console.log('Valor que causou o erro:', tickersRaw);
                }
            } else {
                console.log('Atributo data-tickers vazio ou inválido');
            }
        } catch (parseError) {
            console.error('Erro ao processar JSON de tickers:', parseError);
            // Se falhar, coletar diretamente da tabela
            tickers = [];
        }
        
        // Se não houver tickers do atributo, reunir dos elementos tr
        if (!tickers || tickers.length === 0) {
            console.log('Coletando tickers diretamente das linhas da tabela');
            tickers = [];
            // Procurar em qualquer linha da tabela que tenha data-ticker, para ser mais flexível
            document.querySelectorAll('tr[data-ticker], tr.asset-row').forEach(row => {
                const ticker = row.getAttribute('data-ticker');
                const hasMarketPrice = row.getAttribute('data-has-market-price');
                console.log(`Linha da tabela: ticker=${ticker}, has_market_price=${hasMarketPrice}`);
                
                // Verificar se é um ticker que pode ter preço de mercado
                // Tratar diferentes formatos de valor booleano (true, True, 1, etc.)
                if (ticker && ticker.trim() !== '' && 
                    (hasMarketPrice === 'True' || hasMarketPrice === 'true' || hasMarketPrice === '1' || hasMarketPrice === true)) {
                    tickers.push(ticker);
                    console.log(`Adicionado ticker ${ticker} da tabela`);
                } else if (ticker) {
                    console.log(`Ticker ${ticker} ignorado - has_market_price=${hasMarketPrice}`);
                }
            });
        }
        
        if (!tickers || tickers.length === 0) {
            console.log('Nenhum ticker encontrado para buscar preços');
            return;
        }
        
        console.log('Tickers finais para busca:', tickers);
        
        // Mostrar indicador de carregamento
        const loadingIndicator = document.getElementById('loading-prices');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'inline-block';
            console.log('Indicador de carregamento exibido');
        } else {
            console.log('Indicador de carregamento não encontrado');
        }
        
        // Iniciar busca de preços automaticamente ao carregar a página
        fetchAndUpdatePrices(tickers);
    } catch (error) {
        console.error('Erro ao inicializar o carregamento de preços:', error);
    }
});

// Função para buscar e atualizar preços (ponto de entrada)
function fetchAndUpdatePrices(tickers) {
    console.log('=== INICIANDO ATUALIZAÇÃO DE PREÇOS ===');
    console.log('Tickers recebidos para busca:', tickers);
    
    // Mostrar indicador de carregamento global
    const refreshButton = document.getElementById('refresh-prices-btn');
    if (refreshButton) {
        const originalText = refreshButton.innerHTML;
        refreshButton.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> Atualizando...';
        refreshButton.disabled = true;
        
        // Restaurar botão após a conclusão
        setTimeout(() => {
            refreshButton.innerHTML = originalText;
            refreshButton.disabled = false;
        }, 5000);
    }
    
    // Invocar a função existente para buscar preços
    fetchPrices(tickers);
}

// Função para buscar preços atuais dos ativos
function fetchPrices(inputTickers) {
    console.log('=== INICIANDO BUSCA DE PREÇOS ===');
    
    // Mostrar células de carregamento
    const loadingIndicators = document.querySelectorAll('.current-price-cell, .current-price');
    console.log(`Encontrados ${loadingIndicators.length} indicadores de carregamento`);
    
    loadingIndicators.forEach(indicator => {
        indicator.innerHTML = '<small class="text-muted"><i class="bi bi-arrow-repeat spin"></i> Carregando...</small>';
    });

    // Coletar tickers para enviar ao servidor
    const tickers = inputTickers || [];
    const hasMarketPriceMap = {};
    
    // Se não recebeu tickers como parâmetro, coleta da tabela
    if (!inputTickers || inputTickers.length === 0) {
        console.log('Nenhum ticker fornecido como parâmetro, coletando da tabela');
        document.querySelectorAll('tr[data-ticker], tr.asset-row').forEach(row => {
            const ticker = row.getAttribute('data-ticker');
            // Considerar diferentes formas de representar o valor booleano
            const hasMarketPriceAttr = row.getAttribute('data-has-market-price');
            console.log(`Verificando has_market_price para ${ticker}: valor=${hasMarketPriceAttr}, tipo=${typeof hasMarketPriceAttr}`);
            
            // Aceitar qualquer valor que seja considerado "verdadeiro"
            const hasMarketPrice = hasMarketPriceAttr === 'True' || 
                                 hasMarketPriceAttr === 'true' || 
                                 hasMarketPriceAttr === '1' || 
                                 hasMarketPriceAttr === true;
            
            if (ticker && ticker.trim() !== '') {
                tickers.push(ticker);
                hasMarketPriceMap[ticker] = hasMarketPrice;
                console.log(`Adicionado ticker ${ticker} (has_market_price: ${hasMarketPrice})`);
            }
        });
    }
    
    // Verificar se há tickers para buscar
    if (tickers.length === 0) {
        console.log('Nenhum ticker para buscar');
        loadingIndicators.forEach(indicator => {
            indicator.innerHTML = '<small class="text-muted">N/A</small>';
        });
        return;
    }
    
    console.log(`Buscando preços para ${tickers.length} tickers:`, tickers);
    console.log('Mapa de has_market_price:', hasMarketPriceMap);
    
    // Solicitar preços via API
    fetch('/api/prices', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify({
            tickers: tickers,
            hasMarketPriceMap: hasMarketPriceMap
        })
    })
    .then(response => {
        console.log('Resposta HTTP recebida, status:', response.status);
        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Resposta da API de preços:', data);
        
        if (data && data.prices) {
            console.log('Dados de preços recebidos', Object.keys(data.prices).length, 'preços');
            // Atualizar preços na interface
            updatePrices(data.prices);
            
            // Atualizar o gráfico de desempenho, se a função existir
            if (typeof createPerformanceChart === 'function') {
                try {
                    console.log('Tentando atualizar o gráfico de desempenho');
                    createPerformanceChart(true);
                } catch (chartError) {
                    console.error('Erro ao atualizar o gráfico de desempenho:', chartError);
                }
            }
        } else {
            console.error('Resposta da API não contém dados de preços válidos:', data);
            loadingIndicators.forEach(indicator => {
                indicator.innerHTML = '<small class="text-muted">Indisponível</small>';
            });
        }
    })
    .catch(error => {
        console.error('Erro ao buscar preços:', error);
        loadingIndicators.forEach(indicator => {
            indicator.innerHTML = '<small class="text-danger">Erro</small>';
        });
    });
}

// Função para atualizar preços na interface
function updatePrices(pricesData) {
    console.log('=== ATUALIZANDO PREÇOS NA INTERFACE ===');
    console.log('Atualizando preços com dados:', pricesData);
    
    if (!pricesData || Object.keys(pricesData).length === 0) {
        console.warn('Dados de preços vazios ou inválidos');
        const loadingIndicators = document.querySelectorAll('.current-price-cell, .current-price');
        loadingIndicators.forEach(indicator => {
            indicator.innerHTML = '<small class="text-muted">Indisponível</small>';
        });
        return;
    }
    
    // Variáveis para calcular o total
    let totalValue = 0;
    let totalCurrentValue = 0;
    let assetsWithPrice = 0;
    let rendaFixaTotalValue = 0; // Para somar ativos de renda fixa
    
    // Atualizar cada ticker na tabela
    document.querySelectorAll('tr[data-ticker], tr.asset-row').forEach(row => {
        try {
            const ticker = row.getAttribute('data-ticker');
            if (!ticker) {
                console.log('Linha sem ticker, ignorando');
                return;
            }
            
            // Verificar se o elemento tem a classe asset-row (para compatibilidade com diferentes templates)
            console.log(`Processando linha para ticker: ${ticker}, classe: ${row.className}`);
            
            // Obter dados diretamente dos atributos data- da linha
            const quantity = parseFloat(row.getAttribute('data-quantity') || 0);
            const avgPrice = parseFloat(row.getAttribute('data-avg-price') || 0);
            const assetTotalValue = parseFloat(row.getAttribute('data-total-value') || 0);
            const hasMarketPrice = row.getAttribute('data-has-market-price') === 'True' || 
                              row.getAttribute('data-has-market-price') === 'true' || 
                              row.getAttribute('data-has-market-price') === '1';
            
            console.log(`Processando ticker ${ticker}: quantidade=${quantity}, preço médio=${avgPrice}, valor total=${assetTotalValue}, has_market_price=${hasMarketPrice}`);
            
            totalValue += assetTotalValue;
            
            // Buscar células na linha para atualizar com seletores mais específicos
            const currentPriceCell = row.querySelector('.current-price-cell') || row.querySelector('.current-price');
            
            // Melhorar a detecção da célula de variação - primeiro tenta seletores específicos
            let variationCell = row.querySelector('.variation-cell');
            if (!variationCell) {
                // Se não encontrar diretamente, tenta encontrar o elemento com a classe price-variation
                // ou qualquer elemento que contenha a palavra 'variação' na classe
                const priceVariation = row.querySelector('.price-variation');
                if (priceVariation) {
                    // Se encontrou o elemento de variação interno, usa o pai (td)
                    variationCell = priceVariation.closest('td');
                    console.log(`Encontrada célula de variação via .price-variation para ${ticker}`);
                } else {
                    // Última tentativa - busca pelo índice da coluna (geralmente a 7ª coluna na tabela)
                    const allCells = row.querySelectorAll('td');
                    if (allCells.length >= 7) {
                        // Na maioria dos templates, a coluna de variação é a 7ª (índice 6)
                        variationCell = allCells[6]; 
                        console.log(`Usando célula de variação por posição (7ª coluna) para ${ticker}`);
                    }
                }
            } else {
                console.log(`Encontrada célula de variação via .variation-cell para ${ticker}`);
            }
            
            const currentValueCell = row.querySelector('.current-value-cell') || row.querySelector('.current-value');
            
            console.log(`Células encontradas para ${ticker}: priceCell=${!!currentPriceCell}, variationCell=${!!variationCell}, valueCell=${!!currentValueCell}`);
            
            // TRATAMENTO ESPECÍFICO PARA ATIVOS DE RENDA FIXA (sem preço de mercado)
            if (!hasMarketPrice) {
                console.log(`${ticker} é um ativo de renda fixa, verificando dados pré-carregados`);
                
                // Verificar se já temos dados pré-calculados pelo servidor
                const currentPrice = parseFloat(row.getAttribute('data-current-price') || 0);
                const currentValue = parseFloat(row.getAttribute('data-current-value') || 0);
                const variationValue = parseFloat(row.getAttribute('data-variation-value') || 0);
                
                if (currentPrice > 0 && currentValue > 0) {
                    console.log(`Dados pré-carregados encontrados para ${ticker}: preço=${currentPrice}, valor=${currentValue}`);
                    
                    // Calcular variação
                    const variation = avgPrice > 0 ? ((currentPrice - avgPrice) / avgPrice) * 100 : 0;
                    
                    // Atualizar células na UI se existirem
                    if (currentPriceCell) {
                        currentPriceCell.textContent = `R$ ${currentPrice.toFixed(2)}`;
                    }
                    
                    if (variationCell) {
                        const variationClass = variation >= 0 ? 'text-success' : 'text-danger';
                        const variationIcon = variation >= 0 ? 
                            '<i class="bi bi-arrow-up-circle-fill"></i>' : 
                            '<i class="bi bi-arrow-down-circle-fill"></i>';
                        
                        variationCell.innerHTML = `
                            <div class="d-flex">
                                <span class="${variationClass}">
                                    ${variationIcon}
                                    ${variation.toFixed(2)}%
                                </span>
                                <span class="ms-2 small variation-value-cell ${variationClass}">
                                    (R$ ${variationValue.toFixed(2)})
                                </span>
                            </div>
                        `;
                    }
                    
                    if (currentValueCell) {
                        currentValueCell.textContent = `R$ ${currentValue.toFixed(2)}`;
                    }
                    
                    // Somar ao total geral
                    totalCurrentValue += currentValue;
                    rendaFixaTotalValue += currentValue;
                    assetsWithPrice++;
                    
                    console.log(`Ativo de renda fixa ${ticker} somado aos totais: valor atual=${currentValue}`);
                } else {
                    // Se não temos dados pré-carregados, usar o valor do custo
                    console.log(`Sem dados atualizados para renda fixa ${ticker}, usando valor de custo: ${assetTotalValue}`);
                    totalCurrentValue += assetTotalValue;
                    rendaFixaTotalValue += assetTotalValue;
                    
                    // Manter o valor existente na interface
                    if (currentPriceCell && currentPriceCell.textContent.includes('--')) {
                        currentPriceCell.innerHTML = '<span class="text-muted">N/A</span>';
                    }
                    
                    if (variationCell && variationCell.textContent.includes('--')) {
                        variationCell.innerHTML = '<span class="text-muted">N/A</span>';
                    }
                }
                
                return; // Encerrar o processamento para este ativo
            }
            
            // PROCESSAMENTO DE ATIVOS COM PREÇO DE MERCADO
            let currentPrice = null;
            if (ticker in pricesData) {
                if (typeof pricesData[ticker] === 'object' && pricesData[ticker] !== null) {
                    // Se for um objeto com propriedade price
                    if ('price' in pricesData[ticker]) {
                        currentPrice = parseFloat(pricesData[ticker].price);
                        console.log(`Ticker ${ticker}: preço extraído do objeto price: ${currentPrice}`);
                    }
                } else if (!isNaN(parseFloat(pricesData[ticker]))) {
                    // Se for diretamente um número
                    currentPrice = parseFloat(pricesData[ticker]);
                    console.log(`Ticker ${ticker}: preço extraído diretamente: ${currentPrice}`);
                }
            }
            
            console.log(`Ticker ${ticker}: preço atual final=${currentPrice}, válido=${currentPrice !== null && !isNaN(currentPrice) && currentPrice > 0}`);
            
            if (currentPrice !== null && !isNaN(currentPrice) && currentPrice > 0) {
                // Atualizar células na UI
                if (currentPriceCell) {
                    currentPriceCell.textContent = `R$ ${currentPrice.toFixed(2)}`;
                    currentPriceCell.classList.remove('loading-indicator');
                    console.log(`Preço atualizado para ${ticker}: R$ ${currentPrice.toFixed(2)}`);
                }
                
                // Calcular variação
                if (avgPrice > 0 && variationCell) {
                    console.log(`Calculando variação para ${ticker}: preço atual=${currentPrice}, preço médio=${avgPrice}`);
                    
                    const variation = ((currentPrice - avgPrice) / avgPrice) * 100;
                    const variationClass = variation >= 0 ? 'text-success' : 'text-danger';
                    const variationIcon = variation >= 0 ? 
                        '<i class="bi bi-arrow-up-circle-fill"></i>' : 
                        '<i class="bi bi-arrow-down-circle-fill"></i>';
                    
                    // Calcular valor atual e variação em valor
                    const currentTotalValue = currentPrice * quantity;
                    const variationValue = currentTotalValue - assetTotalValue;
                    
                    console.log(`${ticker}: variação calculada=${variation.toFixed(2)}%, valor atual=${currentTotalValue.toFixed(2)}, variação em valor=${variationValue.toFixed(2)}`);
                    
                    // Atualizar célula de variação - CORRIGIDO PARA MOSTRAR VALOR DIFERENTE DA CÉLULA DE VALOR TOTAL
                    variationCell.innerHTML = `
                        <div class="d-flex">
                            <span class="${variationClass}">
                                ${variationIcon}
                                ${variation.toFixed(2)}%
                            </span>
                            <span class="ms-2 small variation-value-cell ${variationClass}">
                                (R$ ${variationValue.toFixed(2)})
                            </span>
                        </div>
                    `;
                    console.log(`Variação atualizada no DOM para ${ticker}`);
                    
                    // Atualizar o valor total atual - SEPARADO DA ATUALIZAÇÃO DA VARIAÇÃO
                    if (currentValueCell) {
                        currentValueCell.textContent = `R$ ${currentTotalValue.toFixed(2)}`;
                        console.log(`Valor atual atualizado para ${ticker}: R$ ${currentTotalValue.toFixed(2)}`);
                    }
                    
                    // Somar ao total geral
                    totalCurrentValue += currentTotalValue;
                    assetsWithPrice++;
                    
                    // Armazenar os valores calculados nos atributos data-* para uso posterior
                    row.setAttribute('data-current-price', currentPrice);
                    row.setAttribute('data-current-value', currentTotalValue);
                    row.setAttribute('data-variation-value', variationValue);
                    row.setAttribute('data-variation-percent', variation);
                    
                    console.log(`Ticker ${ticker}: valor atual=${currentTotalValue}, variação=${variationValue}`);
                } else {
                    console.warn(`Não foi possível calcular variação para ${ticker}: avgPrice=${avgPrice}, variationCell=${!!variationCell}`);
                }
            } else {
                console.warn(`Preço inválido para ${ticker}: ${currentPrice}`);
                if (currentPriceCell) {
                    currentPriceCell.innerHTML = '<span class="text-muted">--</span>';
                }
                
                if (variationCell) {
                    variationCell.innerHTML = '<span class="text-muted">--</span>';
                }
            }
        } catch (error) {
            console.error(`Erro ao processar linha para ticker ${row.getAttribute('data-ticker')}:`, error);
            // Em caso de erro, garantir que a UI não mostra indicador de carregamento
            const priceCell = row.querySelector('.current-price-cell') || row.querySelector('.current-price');
            
            // Corrigindo o seletor para evitar null reference no tratamento de erros
            let variationCell = row.querySelector('.variation-cell');
            if (!variationCell) {
                const priceVariation = row.querySelector('.price-variation');
                if (priceVariation) {
                    variationCell = priceVariation.parentNode;
                }
            }
            
            if (priceCell) {
                priceCell.innerHTML = '<span class="text-muted">--</span>';
            }
            if (variationCell) {
                variationCell.innerHTML = '<span class="text-muted">--</span>';
            }
        }
    });
    
    console.log(`Totais calculados: valor original=${totalValue}, valor atual=${totalCurrentValue}, ativos com preço=${assetsWithPrice}, valor renda fixa=${rendaFixaTotalValue}`);
    
    // Atualizar totais da carteira
    updatePortfolioTotals(totalValue, totalCurrentValue, assetsWithPrice);
}

// Função auxiliar para atualizar células com N/A
function updateCellsWithNA(priceCell, variationCell, valueCell) {
    if (priceCell) priceCell.innerHTML = '<small class="text-muted">N/A</small>';
    if (variationCell) variationCell.innerHTML = '<small class="text-muted">—</small>';
    if (valueCell) valueCell.innerHTML = '<small class="text-muted">—</small>';
}

// Função para atualizar os totais da carteira
function updatePortfolioTotals(totalValue, totalCurrentValue, assetsWithPrice) {
    console.log(`=== ATUALIZANDO TOTAIS DA CARTEIRA ===`);
    console.log(`Atualizando totais: valor original=${totalValue}, valor atual=${totalCurrentValue}, ativos com preço=${assetsWithPrice}`);
    
    // Verificar se temos pelo menos valor atual, mesmo que não tenha ativos com preço de mercado
    if (totalCurrentValue <= 0) {
        console.warn('Nenhum valor atual válido para exibir');
        
        // Tentar todas as variações possíveis de IDs para os elementos de total
        const totalCurrentValueElements = [
            document.getElementById('total-current-value'),
            document.querySelector('.card-title.text-success'),
            document.querySelector('h4.card-title.text-success')
        ].filter(Boolean);
        
        const totalVariationInfoElements = [
            document.getElementById('total-variation-info'),
            document.getElementById('total-variation-value'),
            document.getElementById('total-variation-percent'),
            document.querySelector('.card-title.text-info'),
            document.querySelector('.card-title.text-warning')
        ].filter(Boolean);
        
        console.log(`Elementos de total encontrados: ${totalCurrentValueElements.length} elementos de valor atual, ${totalVariationInfoElements.length} elementos de variação`);
        
        totalCurrentValueElements.forEach(element => {
            element.innerHTML = 'Dados indisponíveis';
            console.log('Elemento de valor total atualizado para "Dados indisponíveis"');
        });
        
        totalVariationInfoElements.forEach(element => {
            element.className = element.className.replace(/text-\w+/, 'text-muted');
            element.innerHTML = 'Não foi possível calcular a variação';
            console.log('Elemento de variação atualizado para "Não foi possível calcular a variação"');
        });
        
        return;
    }
    
    // Inclui valores de renda fixa pré-carregados do servidor
    let fixedIncomeValue = 0;
    document.querySelectorAll('tr[data-ticker][data-has-market-price="false"][data-current-value]').forEach(row => {
        if (row.closest('#all')) {  // Contar apenas da aba "all" para evitar duplicação
            const currentValue = parseFloat(row.getAttribute('data-current-value') || 0);
            if (!isNaN(currentValue) && currentValue > 0) {
                fixedIncomeValue += currentValue;
                console.log(`Renda fixa incluída no total: ${row.getAttribute('data-ticker')}, R$ ${currentValue.toFixed(2)}`);
            }
        }
    });
    
    if (fixedIncomeValue > 0) {
        totalCurrentValue += fixedIncomeValue;
        console.log(`Adicionado valor de renda fixa aos totais: R$ ${fixedIncomeValue.toFixed(2)}`);
    }
    
    // Calcular variação total
    const totalVariationValue = totalCurrentValue - totalValue;
    const totalVariationPercent = totalValue > 0 ? (totalVariationValue / totalValue) * 100 : 0;
    
    // Definir classes CSS com base na variação
    const variationClass = totalVariationValue >= 0 ? 'text-success' : 'text-danger';
    const variationIcon = totalVariationValue >= 0 
        ? '<i class="bi bi-arrow-up-circle-fill"></i>' 
        : '<i class="bi bi-arrow-down-circle-fill"></i>';
    const variationSign = totalVariationValue >= 0 ? '+' : '';
    
    console.log(`Variação total calculada: ${variationSign}${totalVariationPercent.toFixed(2)}% (${variationSign}R$ ${totalVariationValue.toFixed(2)})`);
    
    // Atualizar elementos do DOM - tenta várias possibilidades para máxima compatibilidade
    const totalCurrentValueElements = [
        document.getElementById('total-current-value'),
        document.querySelector('.card-title.text-success'),
        document.querySelector('h4.card-title.text-success')
    ].filter(Boolean);
    
    const totalVariationValueElements = [
        document.getElementById('total-variation-value'),
        document.querySelector('.card-title.text-info')
    ].filter(Boolean);
    
    const totalVariationPercentElements = [
        document.getElementById('total-variation-info'),
        document.getElementById('total-variation-percent'),
        document.querySelector('.card-title.text-warning')
    ].filter(Boolean);
    
    console.log(`Elementos encontrados para atualização: ${totalCurrentValueElements.length} valor atual, ${totalVariationValueElements.length} variação valor, ${totalVariationPercentElements.length} variação percentual`);
    
    // Atualizar valor atual
    totalCurrentValueElements.forEach(element => {
        if (element.tagName === 'H4') {
            element.innerHTML = `R$ ${totalCurrentValue.toFixed(2)}`;
        } else {
            element.innerHTML = `Atual: R$ ${totalCurrentValue.toFixed(2)}`;
        }
        console.log(`Elemento de valor atual atualizado: ${element.innerHTML}`);
    });
    
    // Atualizar variação em valor
    totalVariationValueElements.forEach(element => {
        element.className = element.className.replace(/text-\w+/, variationClass);
        element.innerHTML = `${variationSign}R$ ${totalVariationValue.toFixed(2)}`;
        console.log(`Elemento de variação em valor atualizado: ${element.innerHTML}`);
    });
    
    // Atualizar variação percentual
    totalVariationPercentElements.forEach(element => {
        element.className = element.className.replace(/text-\w+/, variationClass);
        
        if (element.id === 'total-variation-info') {
            element.innerHTML = `
                ${variationIcon} ${variationSign}${totalVariationPercent.toFixed(2)}% 
                (${variationSign}R$ ${totalVariationValue.toFixed(2)})
            `;
        } else {
            element.innerHTML = `${variationSign}${totalVariationPercent.toFixed(2)}%`;
        }
        console.log(`Elemento de variação percentual atualizado: ${element.innerHTML}`);
    });
}

// Função para coletar tickers no dashboard
function collectTickersFromDashboard() {
    console.log('=== COLETANDO TICKERS NO DASHBOARD ===');
    const marketTickersElement = document.getElementById('market-tickers');
    let tickers = [];

    if (marketTickersElement) {
        console.log('Elemento market-tickers encontrado:', marketTickersElement);
        try {
            let tickersRaw = marketTickersElement.getAttribute('data-tickers');
            console.log('Dados brutos de tickers:', tickersRaw);

            if (tickersRaw && tickersRaw.trim() !== '' && tickersRaw !== '[]' && tickersRaw !== 'null') {
                try {
                    // Correção para JSON incompleto
                    if (tickersRaw.startsWith('[') && !tickersRaw.endsWith(']')) {
                        console.log('Detectado JSON incompleto, corrigindo...');
                        tickersRaw += ']';
                    }

                    // Limpeza adicional para garantir JSON válido
                    tickersRaw = tickersRaw.replace(/'/g, '"').trim();

                    // Verificação extra para garantir que temos um array válido
                    if (tickersRaw === '[') {
                        tickersRaw = '[]';
                    }

                    console.log('JSON após limpeza:', tickersRaw);

                    // Agora tenta fazer o parse do JSON corrigido
                    tickers = JSON.parse(tickersRaw);
                    console.log('Tickers obtidos após correção:', tickers);
                } catch (innerError) {
                    console.error('Erro ao fazer parse do JSON:', innerError);
                    console.log('Valor que causou o erro:', tickersRaw);
                }
            } else {
                console.log('Atributo data-tickers vazio ou inválido');
            }
        } catch (parseError) {
            console.error('Erro ao processar JSON de tickers:', parseError);
        }
    }

    // Se não houver tickers do atributo, reunir dos elementos tr
    if (!tickers || tickers.length === 0) {
        console.log('Coletando tickers diretamente das linhas da tabela');
        document.querySelectorAll('tr[data-ticker]').forEach(row => {
            const ticker = row.getAttribute('data-ticker');
            const hasMarketPrice = row.getAttribute('data-has-market-price');
            console.log(`Linha da tabela: ticker=${ticker}, has_market_price=${hasMarketPrice}`);

            if (ticker && ticker.trim() !== '' &&
                (hasMarketPrice === 'True' || hasMarketPrice === 'true' || hasMarketPrice === '1' || hasMarketPrice === true)) {
                tickers.push(ticker);
                console.log(`Adicionado ticker ${ticker} da tabela`);
            } else if (ticker) {
                console.log(`Ticker ${ticker} ignorado - has_market_price=${hasMarketPrice}`);
            }
        });
    }

    console.log('Tickers finais coletados:', tickers);
    return tickers;
}

// Inicializar gráficos e buscar tickers no dashboard
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard inicializado');
    
    // Coletar tickers no dashboard
    const tickers = collectTickersFromDashboard();

    // Criar os gráficos iniciais
    createOrUpdateTypeChart();
    createPerformanceChart();

    // Buscar preços atuais após carregar a página
    if (tickers.length > 0) {
        fetchAndUpdatePrices(tickers);
    } else {
        console.warn('Nenhum ticker encontrado para buscar preços');
    }

    // Adicionar evento para o botão de atualização de preços
    const refreshButton = document.getElementById('refresh-prices-btn');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            fetchAndUpdatePrices(tickers);
        });
    }
});