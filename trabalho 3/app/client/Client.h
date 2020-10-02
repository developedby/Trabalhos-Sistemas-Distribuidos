#ifndef CLIENT_H
#define CLIENT_H

#include <map>
#include <string>
#include <vector>
#include "enums.h"
#include "Order.h"
#include <ctime>

class MainWindow;
class ClientLoginWindow;

class Client {
    std::map<std::string, double> _quotes;
    std::map<std::string, double> _owned_stock;
    std::vector<Order> _active_orders;
    MainWindow *_gui;
    ClientLoginWindow *_login_gui;
    
public:
    Client();
    void createOrder(OrderType order_type,
                     std::string ticker, 
                     double amount,
                     double price,
                     time_t expiration_datetime);
    void addQuoteAlert(std::string ticker,
                       double lower_limit,
                       double upper_limit);
    void addStockToQuotes(std::string ticker);
    void removeStockFromQuotes(std::string ticker);
    void getCurrentQuotes();
    void notifyLimit(std::string ticker, double current_quote);
    void notifyOrder(std::vector<Transaction> transactions,
                     std::vector<Order> active_orders,
                     std::vector<std::string>expired_orders,
                     std::map<std::string, double> owned_stock);
};

#endif