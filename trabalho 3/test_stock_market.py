import datetime
import time

from app.enums import OrderType
from app.order import Order
from app.stock_market import StockMarket

the_stock_market = StockMarket('./app/stock_market/stock_market.db', use_pyro=False)

print("\n\nteste adicionar cliente")
the_stock_market.add_client("Teste")
the_stock_market.add_client("Teste")
the_stock_market.add_client("Teste2")

print("\n\nverificar ação que não existe")
print(the_stock_market.check_ticker_exists("blablabla"))
print(the_stock_market.get_quotes(["blablabla"]))

print("\n\nverificar ação que existe")
print(the_stock_market.check_ticker_exists("ABEV3.SA"))
print(the_stock_market.get_quotes(["ABEV3.SA"]))

print("\n\nTestando criar uma ordem velha")
order = Order("blalblaaksd", OrderType.SELL, 'blablabla', 1000, 10.0, datetime.datetime.strptime("21/11/06 16:30", "%d/%m/%y %H:%M"))
the_stock_market.create_order(order)

print("\n\nTestando criar uma ordem com um cliente invalido")
order.expiry_date = datetime.datetime.strptime("2021-11-21 16:30:00", "%Y-%m-%d %H:%M:%S")
the_stock_market.create_order(order)

print("\n\nTestando criar uma ordem com uma ação incorreta")
order.type = OrderType.BUY
order.client_name = "Teste"
the_stock_market.create_order(order)

print("\n\nTestando criar uma ordem de venda com uma ação que o cliente não tem")
order.type = OrderType.SELL
order.ticker = "ITSA4.SA"
the_stock_market.create_order(order)

print("\n\nTestando criar uma ordem de compra do mercado")
order.ticker = "ABEV3.SA"
order.type = OrderType.BUY
order.price = 100.0
the_stock_market.create_order(order)

print("\n\nTestando colocar uma ordem de venda na espera para vencer em pouco tempo")
order.expiry_date = datetime.datetime.now() + datetime.timedelta(seconds=2)
order.expiry_date = datetime.datetime.strptime(order.expiry_date.strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")
print(order.expiry_date)
order.type = OrderType.SELL
order.price = 20.0
order.client_name = "Teste"
order.amount = 900
the_stock_market.create_order(order)

time.sleep(3)
print("\n\nTestando criar uma ordem de compra com cliente interno mas vai ser com mercado pq está expirado")
order.expiry_date = datetime.datetime.strptime("21/11/21 16:30", "%d/%m/%y %H:%M")
order.type = OrderType.BUY
order.price = 20.0
order.client_name = "Teste2"
the_stock_market.create_order(order)

print("\n\nRecriando ordem de venda")
order.type = OrderType.SELL
order.price = 20.0
order.client_name = "Teste"
order.amount = 900
the_stock_market.create_order(order)

print("\n\nTestando criar uma ordem de compra com cliente interno")
order.type = OrderType.BUY
order.price = 20.0
order.amount = 800
order.client_name = "Teste2"
the_stock_market.create_order(order)

print("\n\nTestando verificar se o restante da venda vai ser executado pelo banco")
the_stock_market.try_execute_active_orders()

print("\n\nTestando criar uma ordem de compra com cliente interno para ser terminada com o mercado")
order.type = OrderType.BUY
order.price = 20.0
order.amount = 800
order.client_name = "Teste2"
the_stock_market.create_order(order)
