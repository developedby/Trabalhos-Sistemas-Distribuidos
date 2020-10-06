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
#include <cpprest/http_client.h>
#include <cpprest/json.h>
#include <functional>
#include "sse.h"
#include <thread>
#include <QThread>
#include <algorithm>
#include <iomanip>
#include <sstream>
#pragma comment(lib, "cpprest_2_10")

void display_json(web::json::value const & jvalue, utility::string_t const & prefix)
{
    std::cout << prefix << jvalue.serialize() << std::endl;
}

/** Faz a requisição http espeficicamente
 *
 *  @param client               URL HTTP da requisição
 *  @param mtd                  Método HTTP da requisição
 *  @param jvalue               JSON para mandar para o servidor.
 * 
 *  @return                     Task com a resposta da requisição.
 */
pplx::task<web::http::http_response> make_task_request(web::http::client::http_client & client, web::http::method mtd, web::json::value const & jvalue)
{
    return (mtd == web::http::methods::GET || mtd == web::http::methods::HEAD) ? 
           client.request(mtd, "/") : client.request(mtd, "/", jvalue);
}

void make_request_with_json_response(web::http::client::http_client & client, web::http::method mtd, web::json::value const &jvalue, 
                                    std::function<void(web::http::http_response response, web::json::value const &jvalue)> callback_func)
{
    web::http::http_response function_response = web::http::status_codes::BadGateway;
    try
    {
        make_task_request(client, mtd, jvalue)
            .then([&function_response, callback_func](web::http::http_response response)
            {
                function_response = response;
                if (response.status_code() == web::http::status_codes::OK)
                {
                    return response.extract_json();
                }
                return pplx::task_from_result(web::json::value());
            })
            .then([&function_response, callback_func](pplx::task<web::json::value> previousTask)
            {
                try
                {
                    callback_func(function_response, previousTask.get());
                }
                catch (web::http::http_exception const & e)
                {
                    std::cout << e.what() << std::endl;
                }
            })
            .wait();
    }
    catch (web::http::http_exception &e)
    {
        std::cout << "Servidor não disponível" << std::endl;
        exit(0);
    }
}

void make_request_without_json_response(web::http::client::http_client & client, web::http::method mtd, web::json::value const &jvalue, 
                                        std::function<void(web::http::http_response response)> callback_func)
{
    try
    {
        make_task_request(client, mtd, jvalue)
            .then([callback_func](web::http::http_response response)
            {
                callback_func(response);
            })
            .wait();
    }
    catch (web::http::http_exception &e)
    {
        std::cout << "Servidor não disponível" << std::endl;
        exit(0);
    }
}

LoginEvent::LoginEvent(Client &client_, std::string url_) : _client(client_), _url(url_)
{

}

void LoginEvent::_eventsCallback(std::string result)
{
    std::cout << "events callback" << std::endl;
    std::error_code json_error;
    // std::size_t found = result.find("{");
    // std::size_t found2 = result.find("}");
    // if ((found != std::string::npos) && (found != std::string::npos))
    // {
    std::string header("data: ");
    std::size_t found = result.find(header);
    if (found != std::string::npos)
    {
        result = result.substr(found + header.size());
    }
    std::cout << result << std::endl;
    web::json::value ret = web::json::value::parse(result, json_error);
    try
    {
        //Eventos de limit etc
        auto object = ret.as_object();
        for (auto object_iter = object.cbegin(); object_iter != object.cend(); ++object_iter)
        {
            const std::string &key = object_iter->first;
            auto value = object_iter->second;
            std::cout << "key: " << key << ", value: " << value << std::endl;
            
        }
        if (object["event"].as_string() == "limit")
        {
            this->_client.notifyLimit(object["ticker"].as_string(), object["current_quote"].as_double());
        }
        else if (object["event"].as_string() == "order")
        {
            this->_client.notifyOrder(ret);
        }
    }
    catch(const web::json::json_exception& e)
    {
        try
        {
            auto object = ret.as_integer();
            if (object == 0)
            {
                //Login deu certo
                this->_client.connection_status = ClientConnectionStatus::Running;
                this->_client.showMainWindowSignal();
                this->_client.closeLoginWindowSignal();
                this->_client.getState();
            }
            else
            {
                //Erro no login
                this->_client.showLoginErrorSignal();
            }
            
        }
        catch(const std::exception& e)
        {
            std::cout << "Nao conseguiu dar parser no json" << std::endl;
            
        }
        
    } 
}

void LoginEvent::run() 
{
    hold_sse(this->_url, std::bind(&LoginEvent::_eventsCallback, this, std::placeholders::_1));
}

Client::Client(std::string uri) : _login_url(uri + "login"), _status_url(uri + "status"),
                                  _order_url(uri + "order"), _limit_url(uri + "limit"),
                                  _quote_url(uri + "quote"), _close_url(uri + "close"),
                                  _last_order(), connection_status(ClientConnectionStatus::Waiting)
{
    _gui = new MainWindow(*this);
    _login_gui = new ClientLoginWindow(*this);
    _login_gui->show();
    _client_name = "";
    _ticker_to_remove = "";
    _connection_closed = false;
    connect(this, SIGNAL(showLoginErrorSignal()), this->_login_gui, SLOT(showError()));
    connect(this, SIGNAL(closeLoginWindowSignal()), this->_login_gui, SLOT(close()));
    connect(this, SIGNAL(showMainWindowSignal()), this->_gui, SLOT(show()));
}

void Client::_loginCallback(web::http::http_response response)
{
    if (response.status_code() == web::http::status_codes::OK)
    {
        this->connection_status = ClientConnectionStatus::Running;
        this->showMainWindowSignal();
        this->closeLoginWindowSignal();
        this->getState();
    }
    else if(response.status_code() == web::http::status_codes::Forbidden)
    {
        this->showLoginErrorSignal();
    }
}

void Client::login(std::string client_name)
{
    std::string url = this->_login_url + "?client_name=" + client_name;
    this->_client_name = client_name;
    this->_events = new LoginEvent(*this, url);
    
    this->_events->start();
}

void Client::_addStockCallback(web::http::http_response response)
{
    if (response.status_code() == web::http::status_codes::OK)
    {
        this->getCurrentQuotes();
    }
    else if(response.status_code() == web::http::status_codes::NotFound)
    {
        std::string msg = "Não foi possível adicionar essa ação";
        this->_gui->addMessage(msg, true);
    }
}

void Client::addStockToQuotes(std::string ticker)
{
    web::http::client::http_client add_quote(this->_quote_url);
    auto add_stock_json = web::json::value::object();
    add_stock_json["client_name"] = web::json::value::string(this->_client_name);
    add_stock_json["ticker"] = web::json::value::string(ticker);
    make_request_without_json_response(add_quote, web::http::methods::POST, add_stock_json, std::bind(&Client::_addStockCallback, this, std::placeholders::_1));
}

void Client::_removeStockCallback(web::http::http_response response)
{
    if (response.status_code() == web::http::status_codes::OK)
    {
        this->_gui->removeQuotes(this->_ticker_to_remove);
        this->getCurrentQuotes();
    }
    else if(response.status_code() == web::http::status_codes::NotFound)
    {
        std::string msg = "Não foi possível remover essa ação";
        this->_gui->addMessage(msg, true);
    }
}

void Client::removeStockFromQuotes(std::string ticker)
{
    this->_ticker_to_remove = ticker;
    web::http::client::http_client remove_quote(this->_quote_url + "?client_name=" + this->_client_name + "&ticker=" + ticker);
    auto putvalue = web::json::value::object();
    make_request_without_json_response(remove_quote, web::http::methods::DEL, putvalue, std::bind(&Client::_removeStockCallback, this, std::placeholders::_1));
}

void Client::_getStockCallback(web::http::http_response response, web::json::value const &jvalue)
{
    if (response.status_code() == web::http::status_codes::OK)
    {
        this->_gui->clearQuoteAction();
        this->_quotes.clear();
        for (auto object = jvalue.as_object().cbegin(); object != jvalue.as_object().cend(); ++object)
        {
            const std::string &key = object->first;
            double value = object->second.as_double();
            this->_quotes[key] = value;
        }
        for (auto &stock : this->_owned_stock)
        {
            stock.second.second = this->_quotes[stock.first] * stock.second.first;
        }
        
        this->_gui->updateQuotes(this->_quotes);
        this->_gui->updateOwnedQuotes(this->_owned_stock);
    }
    else if(response.status_code() == web::http::status_codes::NotFound)
    {
        std::string msg = "Não foi possível obter essa ação";
        this->_gui->addMessage(msg, true);
    }
}

void Client::getCurrentQuotes()
{
    web::http::client::http_client get_quote(this->_quote_url + "?client_name=" + this->_client_name);
    auto putvalue = web::json::value::object();
    make_request_with_json_response(get_quote, web::http::methods::GET, putvalue, std::bind(&Client::_getStockCallback, this, std::placeholders::_1, std::placeholders::_2));
}

void Client::_createOrderCallback(web::http::http_response response)
{
    if (response.status_code() == web::http::status_codes::OK)
    {
        this->_gui->clearOrderAction();
        this->_gui->updateOrders(this->_active_orders);
    }
    else
    {
        std::vector<Order>::iterator iter = std::find(this->_active_orders.begin(), this->_active_orders.end(), this->_last_order);
        this->_active_orders.erase(iter);
        if(response.status_code() == web::http::status_codes::BadRequest)
        {
            std::string msg = "Não é possível gerar ordem porque a mesma expirou";
            this->_gui->addMessage(msg, true);
        }
        else if(response.status_code() == web::http::status_codes::Forbidden)
        {
            std::string msg = "Não é possível gerar ordem porque a quantidade possuída não é suficiente";
            this->_gui->addMessage(msg, true);
        }
        else if(response.status_code() == web::http::status_codes::NotFound)
        {
            std::string msg = "Não é possível gerar ordem porque a ação não foi encontrada";
            this->_gui->addMessage(msg, true);
        }
    }
    
    
}

void Client::createOrder(OrderType order_type,
                        std::string ticker, 
                        double amount,
                        double price,
                        time_t expiration_datetime)
{
    std::string expiration_datetime_string = time_to_string(&expiration_datetime);
    web::http::client::http_client create_order(this->_order_url);
    Order order_obj(this->_client_name, order_type, ticker, amount, price, expiration_datetime_string);
    this->_active_orders.push_back(order_obj);
    this->_last_order = order_obj;
    web::json::value order_json = order_obj.toJson();
    make_request_without_json_response(create_order, web::http::methods::POST, order_json, std::bind(&Client::_createOrderCallback, this, std::placeholders::_1));
}

void Client::_addAlertCallback(web::http::http_response response)
{
    if (response.status_code() == web::http::status_codes::OK)
    {
        this->_alert_ticker = "";
        this->_gui->clearAlertAction();
        this->_gui->updateAlerts(this->_alerts);
    }
    else
    {
        this->_alerts.erase(this->_alert_ticker);
        if(response.status_code() == web::http::status_codes::BadRequest)
        {
            std::cout << "Não conseguiu criar alerta pq o json está errado" << std::endl;
        }
        else if(response.status_code() == web::http::status_codes::NotFound)
        {
            std::string msg = "Não é possível gerar alerta para ações que não estejam sendo monitoradas";
            this->_gui->addMessage(msg, true);
        }
    }
    
}

void Client::addQuoteAlert(std::string ticker,
                           double lower_limit,
                           double upper_limit)
{
    web::json::value alert_json = web::json::value::object();
    alert_json["ticker"] = web::json::value::string(ticker);
    alert_json["lower_limit"] = web::json::value::number(lower_limit);
    alert_json["upper_limit"] = web::json::value::number(upper_limit);
    alert_json["client_name"] = web::json::value::string(this->_client_name);

    this->_alerts[ticker] = std::make_pair(lower_limit, upper_limit);
    this->_alert_ticker = ticker;

    web::http::client::http_client create_alert(this->_limit_url);
    make_request_without_json_response(create_alert, web::http::methods::POST, alert_json, std::bind(&Client::_addAlertCallback, this, std::placeholders::_1));
}

void Client::notifyLimit(std::string ticker, double current_quote)
{
    std::stringstream stream;
    stream << std::fixed << std::setprecision(2) << current_quote;
    std::string message = "Limite alcançado para \"" + ticker + "\". Valor atual: " + stream.str();
    this->_alerts.erase(ticker);
    this->_gui->removeAlert(ticker);
    this->_gui->addMessage(message);
}

void Client::notifyOrder(web::json::value notification_json)
{
    this->getCurrentQuotes();
    
    auto active_orders = notification_json["active_orders"].as_array();
    auto expired_orders = notification_json["expired_orders"].as_array();
    auto owned_stock = notification_json["owned_stock"].as_object();
    auto transactions = notification_json["transactions"].as_array();

    this->_active_orders.clear();
    for (auto order_iter:active_orders)
    {
        Order order = Order::fromJson(order_iter);
        this->_active_orders.push_back(order);
    }
    this->_gui->updateOrders(this->_active_orders);

    for (auto order_iter:expired_orders)
    {
        std::string msg = "Uma ordem de \"" + order_iter.as_string() + "\" expirou.";
        this->_gui->addMessage(msg);
    }

    this->_owned_stock.clear();
    for (auto stock_iter:owned_stock)
    {
        double value = this->_quotes[stock_iter.first] * stock_iter.second.as_double();
        this->_owned_stock[stock_iter.first] = std::make_pair(stock_iter.second.as_double(), value);
    }
    this->_gui->updateOwnedQuotes(this->_owned_stock);
    
    std::stringstream stream;
    for (auto transaction_iter:transactions)
    {
        Transaction transaction = Transaction::fromJson(transaction_iter);
        std::string oper_name = ((transaction.seller_name == this->_client_name) ? "Vendeu " : "Comprou ");
        stream.str("");
        stream << std::fixed << std::setprecision(2) << transaction.amount;
        std::string amount_str = stream.str();
        stream.str("");
        stream << std::fixed << std::setprecision(2) << transaction.price;
        std::string price_str = stream.str();
        std::string msg =   "Transação executada: " + oper_name + 
                            amount_str + " ações de \"" + transaction.ticker + "\" por " + 
                            price_str + " cada em " + transaction.datetime;
        this->_gui->addMessage(msg);
    }
}

void Client::_getStateCallback(web::http::http_response response, web::json::value const &jvalue_)
{
    if (response.status_code() == web::http::status_codes::OK)
    {
        web::json::value jvalue= jvalue_;
        display_json(jvalue, "Resultado do status: ");
        const auto quotes_json = jvalue["quotes"].as_object();
        const auto orders_json = jvalue["orders"].as_array();
        const auto owned_stock_json = jvalue["owned_stock"].as_object();
        const auto alerts_json = jvalue["alerts"].as_object();

        for (auto quote_iter:quotes_json)
        {
            this->_quotes[quote_iter.first] = quote_iter.second.as_double();
        }
        this->_gui->updateQuotes(this->_quotes);

        for (auto order_iter:orders_json)
        {
            Order order = Order::fromJson(order_iter);
            this->_active_orders.push_back(order);
        }
        this->_gui->updateOrders(this->_active_orders);

        for (auto stock_iter:owned_stock_json)
        {
            double value = this->_quotes[stock_iter.first] * stock_iter.second.as_double();
            this->_owned_stock[stock_iter.first] = std::make_pair(stock_iter.second.as_double(), value);
        }
        this->_gui->updateOwnedQuotes(this->_owned_stock);

        for (auto alert_iter:alerts_json)
        {
            auto alert_values = alert_iter.second.as_array();
            this->_alerts[alert_iter.first] = std::make_pair(alert_values[0].as_double(), alert_values[1].as_double());
        }
        this->_gui->updateAlerts(this->_alerts);
    }
    else if(response.status_code() == web::http::status_codes::BadRequest)
    {
        std::cout << "Pacote inválido" << std::endl;
    }
    else if (response.status_code() == web::http::status_codes::NotFound)
    {
        std::cout << "Cliente desconhecido" << std::endl;
    }
}

void Client::getState()
{
    web::http::client::http_client get_status(this->_status_url + "?client_name=" + this->_client_name);
    web::json::value putvalue;
    make_request_with_json_response(get_status, web::http::methods::GET, putvalue, std::bind(&Client::_getStateCallback, this, std::placeholders::_1, std::placeholders::_2));
}

void Client::_closeCallback(web::http::http_response response)
{
    this->_connection_closed = true;
}

void Client::close()
{
    this->_connection_closed = false;
    web::http::client::http_client close(this->_close_url + "?client_name=" + this->_client_name);
    web::json::value putvalue;
    make_request_without_json_response(close, web::http::methods::GET, putvalue, std::bind(&Client::_closeCallback, this, std::placeholders::_1));
    while (!this->_connection_closed)
    {
        usleep(1000);
    }
    this->_gui->close();
}