#include "Client.h"
#include <map>
#include <string>
#include <vector>
#include "enums.h"
#include "Order.h"
#include <ctime>
#include <unistd.h>
#include "MainWindow.h"
#include "ClientLoginWindow.h"


Client::Client()
{
    _gui = new MainWindow(*this);
    _login_gui = new ClientLoginWindow(*this);
    _login_gui->show();
    _gui->show();
}

void Client::createOrder(OrderType order_type,
                         std::string ticker, 
                         double amount,
                         double price,
                         time_t expiration_datetime)
{

}

void Client::addQuoteAlert(std::string ticker,
                           double lower_limit,
                           double upper_limit)
{
    
}

void Client::addStockToQuotes(std::string ticker)
{

}

void Client::removeStockFromQuotes(std::string ticker)
{

}
    
void Client::getCurrentQuotes()
{

}

void Client::notifyLimit(std::string ticker, double current_quote)
{

}

void Client::notifyOrder(std::vector<Transaction> transactions,
                         std::vector<Order> active_orders,
                         std::vector<std::string>expired_orders,
                         std::map<std::string, double> owned_stock)
{

}