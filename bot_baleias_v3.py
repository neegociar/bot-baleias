# bot_baleias_v3.py - VERSÃO COM NOVAS MOEDAS
import warnings
warnings.filterwarnings('ignore')
import os
os.environ['PYTHONWARNINGS'] = 'ignore'

import asyncio
import json
import requests
import time
import logging
import websockets
import threading
from datetime import datetime, timedelta
from binance.client import Client
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

# ============================================
# CORES
# ============================================
class Cores:
    RESET = '\033[0m'
    VERMELHO = '\033[91m'
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    AZUL = '\033[94m'
    MAGENTA = '\033[95m'
    CIANO = '\033[96m'
    BRANCO = '\033[97m'
    CINZA = '\033[90m'
    NEGRITO = '\033[1m'
    VERDE_NEGRITO = '\033[1;92m'
    VERMELHO_NEGRITO = '\033[1;91m'
    AMARELO_NEGRITO = '\033[1;93m'
    AZUL_NEGRITO = '\033[1;94m'
    MAGENTA_NEGRITO = '\033[1;95m'
    CIANO_NEGRITO = '\033[1;96m'
    FUNDO_VERDE = '\033[42m'
    FUNDO_VERMELHO = '\033[41m'

os.system('')

# ============================================
# CONFIGURAÇÕES
# ============================================
COINALYZE_API_KEY = 'd7d76e7b-e364-46d5-8ccd-97d47646b47f'
BINANCE_API_KEY = 'TnryN2GXtAWFutlf5aIimGvPyqu95hjBJXTbwHNMiHeQr1YDFPiZ0EJJziDH6aUB'
BINANCE_SECRET_KEY = 'gZzrhHqktzYeuBwj66Sv8KxS0mnqsF8dNhlUA6LL7rdkRlAiEQzhTGx88CkRcSAv'

TELEGRAM_TOKEN = "8207229215:AAGNJfXhQm2Xmqzv6XQ8pZ_8Ml-iaZl387Y"
TELEGRAM_CHAT_ID = "5869218072"

# ============================================
# MOEDAS ATUALIZADAS (com novas adições)
# ============================================
MOEDAS = {
    # TOP PERFORMERS (manter)
    'SOL': {
        'symbol': 'SOLUSDT', 
        'oi_symbol': 'SOL-USDT-SWAP', 
        'quantidade': 1.0, 
        'cor': Cores.MAGENTA_NEGRITO, 
        'ativa': True,
        'alavancagem': 5,
        'stop_pct': 0.02,
        'take_pct': 0.018
    },
    'SUI': {
        'symbol': 'SUIUSDT', 
        'oi_symbol': 'SUI-USDT-SWAP', 
        'quantidade': 30, 
        'cor': Cores.AZUL_NEGRITO, 
        'ativa': True,
        'alavancagem': 5,
        'stop_pct': 0.02,
        'take_pct': 0.018
    },
    'ETH': {
        'symbol': 'ETHUSDT', 
        'oi_symbol': 'ETH-USDT-SWAP', 
        'quantidade': 0.05, 
        'cor': Cores.CIANO_NEGRITO, 
        'ativa': True,
        'alavancagem': 3,
        'stop_pct': 0.02,
        'take_pct': 0.018
    },
    'BTC': {
        'symbol': 'BTCUSDT', 
        'oi_symbol': 'BTC-USDT-SWAP', 
        'quantidade': 0.003, 
        'cor': Cores.VERDE_NEGRITO, 
        'ativa': True,
        'alavancagem': 1,
        'stop_pct': 0.02,
        'take_pct': 0.018
    },
    
    # NOVAS MOEDAS (TOP DO BACKTEST)
    'OP': {
        'symbol': 'OPUSDT', 
        'oi_symbol': 'OP-USDT-SWAP', 
        'quantidade': 15, 
        'cor': Cores.AMARELO_NEGRITO, 
        'ativa': True,
        'alavancagem': 5,
        'stop_pct': 0.02,
        'take_pct': 0.018
    },
    'DOT': {
        'symbol': 'DOTUSDT', 
        'oi_symbol': 'DOT-USDT-SWAP', 
        'quantidade': 10, 
        'cor': Cores.CIANO_NEGRITO, 
        'ativa': True,
        'alavancagem': 5,
        'stop_pct': 0.02,
        'take_pct': 0.018
    },
    'NEAR': {
        'symbol': 'NEARUSDT', 
        'oi_symbol': 'NEAR-USDT-SWAP', 
        'quantidade': 20, 
        'cor': Cores.MAGENTA_NEGRITO, 
        'ativa': True,
        'alavancagem': 5,
        'stop_pct': 0.02,
        'take_pct': 0.018
    }
}

GATILHO_QUEDA = -0.5
GATILHO_SUBIDA = 0.5
INTERVALO_OI = 15

precos = {moeda: 0 for moeda in MOEDAS}
ultimos_oi = {moeda: None for moeda in MOEDAS}
scores = {moeda: 0 for moeda in MOEDAS}
fundings = {moeda: 0 for moeda in MOEDAS}

# ============================================
# CARREGAR MODELOS ML
# ============================================
modelos_ml = {}

print(f"\n{Cores.MAGENTA_NEGRITO}{'='*70}{Cores.RESET}")
print(f"{Cores.MAGENTA_NEGRITO}     🤖 CARREGANDO MODELOS RANDOM FOREST 🤖{Cores.RESET}")
print(f"{Cores.MAGENTA_NEGRITO}{'='*70}{Cores.RESET}")

for moeda in MOEDAS:
    arquivo = f"ml_model_{moeda}_90d.pkl"
    if os.path.exists(arquivo):
        try:
            dados = joblib.load(arquivo)
            modelos_ml[moeda] = {
                'modelo': dados['modelo'],
                'scaler': dados.get('scaler'),
                'acuracia': dados.get('acuracia', 0)
            }
            print(f"{Cores.VERDE}✅ Random Forest carregado para {moeda} (acurácia: {modelos_ml[moeda]['acuracia']:.1%}){Cores.RESET}")
        except:
            modelos_ml[moeda] = None
            print(f"{Cores.VERMELHO}❌ Erro ao carregar modelo para {moeda}{Cores.RESET}")
    else:
        modelos_ml[moeda] = None
        print(f"{Cores.AMARELO}⚠️ Modelo não encontrado para {moeda} (treinando...){Cores.RESET}")

# ============================================
# FUNÇÕES
# ============================================
def enviar_telegram(mensagem):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
        requests.post(url, json=payload, timeout=5)
    except:
        pass

def prever_ml(moeda, dados_atual):
    """Faz predição usando o modelo"""
    modelo_info = modelos_ml.get(moeda)
    if not modelo_info or not modelo_info['modelo']:
        return None, 0
    
    try:
        features = np.array([[
            dados_atual['variacao_oi'] / 100,
            dados_atual['volatilidade'],
            dados_atual['momentum'],
            dados_atual.get('tendencia_5h', 0),
            dados_atual.get('tendencia_24h', 0)
        ]])
        
        predicao = modelo_info['modelo'].predict(features)[0]
        proba = modelo_info['modelo'].predict_proba(features)[0]
        
        if predicao == 1:
            return 'COMPRA', max(proba)
        else:
            return 'VENDA', max(proba)
    except:
        return None, 0

class BotML:
    def __init__(self):
        self.client = None
        
    def conectar_binance(self):
        try:
            self.client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
            self.client.ping()
            print(f"{Cores.VERDE}✅ Binance conectada{Cores.RESET}")
            return True
        except Exception as e:
            print(f"{Cores.VERMELHO}❌ Erro: {e}{Cores.RESET}")
            return False
    
    async def websocket_precos(self):
        streams = []
        for moeda, config in MOEDAS.items():
            if config['ativa']:
                streams.append(f"{config['symbol'].lower()}@trade")
        
        uri = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"
        
        while True:
            try:
                async with websockets.connect(uri) as ws:
                    print(f"{Cores.VERDE}✅ WebSocket conectado! Monitorando {len(streams)} moedas{Cores.RESET}")
                    while True:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        if 'data' in data:
                            trade = data['data']
                            for moeda, config in MOEDAS.items():
                                if config['symbol'] == trade['s']:
                                    precos[moeda] = float(trade['p'])
            except Exception as e:
                print(f"{Cores.VERMELHO}❌ WebSocket erro: {e}{Cores.RESET}")
                await asyncio.sleep(5)
    
    def obter_oi_okx(self, moeda):
        config = MOEDAS[moeda]
        try:
            url = "https://www.okx.com/api/v5/public/open-interest"
            params = {"instId": config['oi_symbol']}
            r = requests.get(url, params=params, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get('code') == '0':
                    oi_data = data.get('data', [])
                    if oi_data:
                        oi_btc = float(oi_data[0]['oiCcy'])
                        return oi_btc * precos[moeda]
        except:
            pass
        return None
    
    def obter_funding_rate(self, moeda):
        config = MOEDAS[moeda]
        try:
            url = "https://api.coinalyze.net/v1/funding-rate"
            params = {'api_key': COINALYZE_API_KEY, 'symbols': f'{config["symbol"]}_PERP.A'}
            r = requests.get(url, params=params, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data:
                    return float(data[0]['value'])
        except:
            pass
        return 0
    
    def calcular_score(self, variacao, funding):
        score = 50
        score += min((abs(variacao) / 0.5) * 25, 25)
        if (variacao > 0 and funding > 0.005) or (variacao < 0 and funding < -0.005):
            score += 15
        elif (variacao > 0 and funding > 0) or (variacao < 0 and funding < 0):
            score += 8
        if abs(variacao) > 1.0:
            score += 10
        elif abs(variacao) > 0.8:
            score += 5
        return min(100, max(0, score))
    
    def mostrar_status(self, moeda, preco, oi, variacao, funding, score, pred_ml, conf_ml):
        config = MOEDAS[moeda]
        
        var_cor = f"{Cores.VERDE}+{variacao:.2f}%{Cores.RESET}" if variacao > 0 else f"{Cores.VERMELHO}{variacao:.2f}%{Cores.RESET}" if variacao < 0 else f"{Cores.CINZA}{variacao:.2f}%{Cores.RESET}"
        fund_cor = f"{Cores.VERDE}{funding*100:.4f}%{Cores.RESET}" if funding > 0 else f"{Cores.VERMELHO}{funding*100:.4f}%{Cores.RESET}" if funding < 0 else f"{Cores.CINZA}{funding*100:.4f}%{Cores.RESET}"
        score_cor = f"{Cores.VERDE_NEGRITO}{score:.0f}{Cores.RESET}" if score >= 70 else f"{Cores.AMARELO}{score:.0f}{Cores.RESET}" if score >= 50 else f"{Cores.VERMELHO}{score:.0f}{Cores.RESET}"
        
        nivel = "🟢 MUITO FORTE" if score >= 85 else "🟡 FORTE" if score >= 70 else "🟠 MÉDIA" if score >= 60 else "🔵 FRACA" if score >= 50 else "🔴 MUITO FRACA"
        
        print(f"\n{Cores.AZUL}{'─'*70}{Cores.RESET}")
        print(f"{config['cor']}🕐 {datetime.now().strftime('%H:%M:%S')} | {moeda}{Cores.RESET}")
        print(f"{Cores.CIANO}⚡ PREÇO:{Cores.RESET} ${preco:,.2f}")
        print(f"{Cores.CIANO}📊 OI:{Cores.RESET} ${oi/1_000_000:.2f}M")
        print(f"{Cores.CIANO}📈 Variação:{Cores.RESET} {var_cor}")
        print(f"{Cores.CIANO}💸 Funding:{Cores.RESET} {fund_cor}")
        print(f"{Cores.CIANO}🎯 SCORE:{Cores.RESET} {score_cor} | {nivel}")
        
        if pred_ml:
            ml_cor = Cores.VERDE if conf_ml > 0.7 else Cores.AMARELO if conf_ml > 0.5 else Cores.VERMELHO
            print(f"{Cores.CIANO}🤖 RandomForest:{Cores.RESET} {ml_cor}{pred_ml} (conf: {conf_ml*100:.0f}%){Cores.RESET}")
        
        # Mostrar alavancagem recomendada
        alav = config['alavancagem']
        print(f"{Cores.CIANO}⚡ ALAVANCAGEM:{Cores.RESET} {alav}x")
    
    def verificar_gatilhos(self):
        for moeda, config in MOEDAS.items():
            if not config['ativa']:
                continue
            oi_atual = self.obter_oi_okx(moeda)
            preco = precos[moeda]
            if oi_atual and preco > 0:
                if ultimos_oi[moeda] is not None:
                    variacao = ((oi_atual - ultimos_oi[moeda]) / ultimos_oi[moeda]) * 100
                else:
                    variacao = 0
                ultimos_oi[moeda] = oi_atual
                funding = self.obter_funding_rate(moeda)
                score = self.calcular_score(variacao, funding)
                
                dados_ml = {
                    'variacao_oi': variacao,
                    'volatilidade': abs(variacao) / 100,
                    'momentum': variacao / 100,
                    'tendencia_5h': variacao / 100,
                    'tendencia_24h': variacao / 100
                }
                pred_ml, conf_ml = prever_ml(moeda, dados_ml)
                
                self.mostrar_status(moeda, preco, oi_atual, variacao, funding, score, pred_ml, conf_ml)
                
                # Gatilho para alerta (score alto + ML confirma)
                if score >= 70 and conf_ml > 0.6:
                    if variacao < GATILHO_QUEDA and pred_ml == 'VENDA':
                        self.enviar_alerta_venda(moeda, preco, variacao, score, conf_ml)
                    elif variacao > GATILHO_SUBIDA and pred_ml == 'COMPRA':
                        self.enviar_alerta_compra(moeda, preco, variacao, score, conf_ml)
    
    def enviar_alerta_compra(self, moeda, preco, variacao, score, conf):
        config = MOEDAS[moeda]
        alav = config['alavancagem']
        stop = preco * (1 - config['stop_pct'])
        take = preco * (1 + config['take_pct'])
        
        msg = f"""🐋 <b>ALERTA COMPRA LONG - {moeda}</b>

💰 <b>Entrada:</b> ${preco:.2f}
📊 <b>Variação OI:</b> +{variacao:.2f}%
🎯 <b>Score:</b> {score:.0f}
🤖 <b>ML:</b> COMPRA (conf: {conf*100:.0f}%)
💡 <b>Quantidade:</b> {config['quantidade']} {moeda}
⚡ <b>Alavancagem:</b> {alav}x

📍 <b>Stop Loss:</b> ${stop:.2f} (-{config['stop_pct']*100:.0f}%)
📍 <b>Take Profit:</b> ${take:.2f} (+{config['take_pct']*100:.0f}%)

🚀 Operar manualmente na Binance"""
        enviar_telegram(msg)
        
        print(f"\n{Cores.FUNDO_VERDE}{Cores.NEGRITO}🔔 ALERTA ENVIADO PARA TELEGRAM!{Cores.RESET}")
    
    def enviar_alerta_venda(self, moeda, preco, variacao, score, conf):
        config = MOEDAS[moeda]
        alav = config['alavancagem']
        stop = preco * (1 + config['stop_pct'])
        take = preco * (1 - config['take_pct'])
        
        msg = f"""🔴 <b>ALERTA VENDA SHORT - {moeda}</b>

💰 <b>Entrada:</b> ${preco:.2f}
📊 <b>Variação OI:</b> {variacao:.2f}%
🎯 <b>Score:</b> {score:.0f}
🤖 <b>ML:</b> VENDA (conf: {conf*100:.0f}%)
💡 <b>Quantidade:</b> {config['quantidade']} {moeda}
⚡ <b>Alavancagem:</b> {alav}x

📍 <b>Stop Loss:</b> ${stop:.2f} (+{config['stop_pct']*100:.0f}%)
📍 <b>Take Profit:</b> ${take:.2f} (-{config['take_pct']*100:.0f}%)

🚀 Operar manualmente na Binance"""
        enviar_telegram(msg)
        
        print(f"\n{Cores.FUNDO_VERMELHO}{Cores.NEGRITO}🔔 ALERTA ENVIADO PARA TELEGRAM!{Cores.RESET}")
    
    def executar_loop_oi(self):
        while True:
            try:
                self.verificar_gatilhos()
                time.sleep(INTERVALO_OI)
            except Exception as e:
                print(f"{Cores.VERMELHO}❌ Erro: {e}{Cores.RESET}")
                time.sleep(INTERVALO_OI)
    
    def executar(self):
        print(f"\n{Cores.MAGENTA_NEGRITO}{'='*80}{Cores.RESET}")
        print(f"{Cores.MAGENTA_NEGRITO}     🐋 ROBÔ DAS BALEIAS - PORTFÓLIO OTIMIZADO 🐋{Cores.RESET}")
        print(f"{Cores.MAGENTA_NEGRITO}{'='*80}{Cores.RESET}")
        print(f"{Cores.VERDE}📱 Telegram ativado!{Cores.RESET}")
        print(f"{Cores.CIANO}🤖 Moedas monitoradas:{Cores.RESET}")
        
        for moeda, config in MOEDAS.items():
            if config['ativa']:
                print(f"   {config['cor']}{moeda}{Cores.RESET} - Alav: {config['alavancagem']}x | Qtd: {config['quantidade']}")
        
        print(f"{Cores.MAGENTA_NEGRITO}{'='*80}{Cores.RESET}\n")
        
        if not self.conectar_binance():
            return
        
        def rodar_websocket():
            asyncio.run(self.websocket_precos())
        
        threading.Thread(target=rodar_websocket, daemon=True).start()
        
        print(f"{Cores.CIANO}🚀 Iniciando monitoramento...{Cores.RESET}")
        print(f"{Cores.VERDE}⚡ PREÇO em tempo real{Cores.RESET}")
        print(f"{Cores.AMARELO}📊 OI atualizando a cada {INTERVALO_OI}s{Cores.RESET}")
        print(f"{Cores.MAGENTA}🤖 Random Forest analisando {len(MOEDAS)} moedas{Cores.RESET}\n")
        
        self.executar_loop_oi()


if __name__ == "__main__":
    bot = BotML()
    bot.executar()