# Trabalho 2 - Mercado da Bolsa de Valores

CSS30 - S71 : Sistemas Distribuídos 2020.2

O sistema consiste de 3 partes:
* StockMarket - Simula a bolsa de valores, usando dados do mercado real. Realiza transações, executando compras e vendas tanto entre os clientes internos, como também entre clientes internos e o mercado real (de forma simulada).
* Homebroker - Servidor do homebroker. Recebe os pedidos dos clientes, enviando-os ao StockMarket. Verifica o StockMarket regularmente, notificando os clientes caso haja algum evento de interesse.
* Client - Cliente do homebroker. Permite obter cotações atualizadas, criar ordens de compra e venda e criar limites de ganho e perda.

## Autores
* Nicolas Abril
* Álefe Felipe Gonçalves Pereira Dias

## Como rodar
1. Abrir o nameserver do Pyro (run_nameserver.sh)
2. Abrir o simulador de bolsa (python3 run_homebroker.py)
3. Abrir o servidor do Homebroker (python3 run_homebroker.py)
4. Abrir o cliente (python3 run_client.py)
5. Inserir o nome de usuário

## Requisitos
* python >= 3.6
* Pyro 5 (https://pypi.org/project/Pyro5/)
* yfinance (https://pypi.org/project/yfinance/)