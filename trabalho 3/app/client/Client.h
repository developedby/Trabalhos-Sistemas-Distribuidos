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
#include <QThread>
#include <utility>

class MainWindow;
class ClientLoginWindow;
class LoginEvent;


enum class ClientConnectionStatus
{
    Waiting,
    Running,
    Close
};


class Client : public QObject {
    Q_OBJECT
    std::map<std::string, double> _quotes; //ticker->price
    std::map<std::string, std::pair<double, double>> _owned_stock; //ticker->(amount, value)
    std::vector<Order> _active_orders;
    std::map<std::string, std::pair<double, double>> _alerts; //ticker->(lower_limit, upper_limit)
    LoginEvent *_events;
    MainWindow *_gui;
    ClientLoginWindow *_login_gui;

    Order _last_order;

    std::string _client_name;
    std::string _ticker_to_remove;
    std::string _alert_ticker;
    std::string _login_url;
    std::string _status_url;
    std::string _order_url;
    std::string _limit_url;
    std::string _quote_url;
    std::string _close_url;

    bool _connection_closed;

    // std::thread *_events_thread;
    // QThread _events_thread;
    // QThread *_events_thread;
    

    void _loginCallback(web::http::http_response response);
    void _addStockCallback(web::http::http_response response);
    void _removeStockCallback(web::http::http_response response);
    void _getStockCallback(web::http::http_response response, web::json::value const &jvalue);
    void _createOrderCallback(web::http::http_response response);
    void _eventsCallback(std::string result);
    void _addAlertCallback(web::http::http_response response);
    void _getStateCallback(web::http::http_response response, web::json::value const &jvalue);
    void _closeCallback(web::http::http_response response);

    friend void make_request_without_json_response(web::http::client::http_client & client, web::http::method mtd, web::json::value const &jvalue, 
                                        std::function<void(web::http::http_response response)> callback_func);

    friend void make_request_with_json_response(web::http::client::http_client & client, web::http::method mtd, web::json::value const &jvalue, 
                                    std::function<void(web::http::http_response response, web::json::value const &jvalue)> callback_func);
    
public:
    ClientConnectionStatus connection_status;

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
    void notifyOrder(web::json::value notification_json);
    void login(std::string client_name);
    void getState();
    void close();
signals:
    void showErrorSignal();
    void closeLoginWindowSignal();
    void showMainWindowSignal();
};

class LoginEvent : public QThread
{
    Q_OBJECT
    Client &_client;
    std::string _url;

    void run() override;
    void _eventsCallback(std::string result);
public:
    LoginEvent(Client &client_, std::string url_);
};

#endif