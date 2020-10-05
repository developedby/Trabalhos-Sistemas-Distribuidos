#ifndef CLIENT_H
#define CLIENT_H

#include <map>
#include <string>
#include <vector>
#include "enums.h"
#include "Order.h"
#include <ctime>
#include <cpprest/http_client.h>
#include <thread>

class MainWindow;
class ClientLoginWindow;

class Client {
    std::map<std::string, double> _quotes;
    std::map<std::string, double> _owned_stock;
    std::vector<Order> _active_orders;
    MainWindow *_gui;
    ClientLoginWindow *_login_gui;

    std::string _client_name;
    std::string _ticker_to_remove;
    std::string _login;
    std::string _status;
    std::string _order;
    std::string _limit;
    std::string _quote;

    std::thread *_events_thread;
    

    void _loginCallback(web::http::http_response response);
    void _addStockCallback(web::http::http_response response);
    void _deleteStockCallback(web::http::http_response response);
    void _getStockCallback(web::http::http_response response, web::json::value const &jvalue);
    void _createOrderCallback(web::http::http_response response);
    void _eventsCallback(std::string result);

    friend void make_request_without_json_response(web::http::client::http_client & client, web::http::method mtd, web::json::value const &jvalue, 
                                        std::function<void(web::http::http_response response)> callback_func);

    friend void make_request_with_json_response(web::http::client::http_client & client, web::http::method mtd, web::json::value const &jvalue, 
                                    std::function<void(web::http::http_response response, web::json::value const &jvalue)> callback_func);
    
public:
    Client(std::string uri);
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
    void login(std::string client_name);


    

};

#endif