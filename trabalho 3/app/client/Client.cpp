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
#pragma comment(lib, "cpprest_2_10")

void display_json(web::json::value const & jvalue, utility::string_t const & prefix)
{
    std::cout << prefix << jvalue.serialize() << std::endl;
}

pplx::task<web::http::http_response> make_task_request(web::http::client::http_client & client, web::http::method mtd, web::json::value const & jvalue)
{
    return (mtd == web::http::methods::GET || mtd == web::http::methods::HEAD) ? 
           client.request(mtd, "/") : client.request(mtd, "/", jvalue);
}

void make_request_with_json_response(web::http::client::http_client & client, web::http::method mtd, web::json::value const &jvalue, 
                                    std::function<void(web::http::http_response response, web::json::value const &jvalue)> callback_func)
{
    web::http::http_response function_response = web::http::status_codes::BadGateway;
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
                std::cout << "Olhando o json, resposta é "<< std::endl;
                callback_func(function_response, previousTask.get());
            }
            catch (web::http::http_exception const & e)
            {
                std::cout << "Erro Olhando o json"<< std::endl;
                std::cout << e.what() << std::endl;
            }
        })
        .wait();
}

void make_request_without_json_response(web::http::client::http_client & client, web::http::method mtd, web::json::value const &jvalue, 
                                        std::function<void(web::http::http_response response)> callback_func)
{
    make_task_request(client, mtd, jvalue)
        .then([callback_func](web::http::http_response response)
        {
            callback_func(response);
        })
        .wait();
}
 
// void make_request(web::http::client::http_client & client, web::http::method mtd, web::json::value const & jvalue, void *callbackfunction())
// {
//     make_task_request(client, mtd, jvalue)
//         .then([](web::http::http_response response)
//         {
//             if (response.status_code() == web::http::status_codes::OK)
//             {
//                 std::cout << "resultado " << response.status_code() << std::endl;
//                 return response.extract_json();
//             }
//             std::cout << "resultado ruim" << response.status_code() << std::endl;
//             return pplx::task_from_result(web::json::value());
//         })
//         .then([](pplx::task<web::json::value> previousTask)
//         {
//             std::cout << "Olhando as coisas"<< std::endl;
//             try
//             {
//                 std::cout << "Olhando o json"<< std::endl;
//                 display_json(previousTask.get(), "R: ");
//             }
//             catch (web::http::http_exception const & e)
//             {
//                 std::cout << "Erro Olhando o json"<< std::endl;
//                 std::cout << e.what() << std::endl;
//             }
//         })
//         .wait();
// }

Client::Client(std::string uri) : _login(uri + "login"), _status(uri + "status"),
                                  _order(uri + "order"), _limit(uri + "limit"),
                                  _quote(uri + "quote")
{
    _gui = new MainWindow(*this);
    _login_gui = new ClientLoginWindow(*this);
    _login_gui->show();
    _client_name = "";
    _ticker_to_remove = "";
}

void Client::addQuoteAlert(std::string ticker,
                           double lower_limit,
                           double upper_limit)
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

void Client::_eventsCallback(std::string result)
{
    std::cout << "events callback" << std::endl;
    std::cout << result << std::endl;

}

void Client::_loginCallback(web::http::http_response response)
{
    if (response.status_code() == web::http::status_codes::OK)
    {
        this->_login_gui->close();
        this->_gui->show();
    }
    else if(response.status_code() == web::http::status_codes::Forbidden)
    {
        this->_login_gui->showError();
    }
}

void Client::login(std::string client_name)
{
    std::string url = this->_login + "?client_name=" + client_name;
    this->_events_thread = new std::thread(hold_sse, url, std::bind(&Client::_eventsCallback, this, std::placeholders::_1));
    
    
}

void Client::_addStockCallback(web::http::http_response response)
{
    if (response.status_code() == web::http::status_codes::OK)
    {
        //TODO: Colocar na GUI
        std::cout << "Conseguiu adicionar stock" << std::endl;
        this->getCurrentQuotes();
    }
    else if(response.status_code() == web::http::status_codes::NotFound)
    {
        //TODO: Colocar mensagem na gui
        std::cout << "Não conseguiu adicionar stock" << std::endl;
        // this->_login_gui->showError();
    }
}

void Client::addStockToQuotes(std::string ticker)
{
    web::http::client::http_client add_quote(this->_quote);
    auto add_stock_json = web::json::value::object();
    add_stock_json["client_name"] = web::json::value::string(this->_client_name);
    add_stock_json["ticker"] = web::json::value::string(ticker);
    make_request_without_json_response(add_quote, web::http::methods::POST, add_stock_json, std::bind(&Client::_addStockCallback, this, std::placeholders::_1));
}

void Client::_deleteStockCallback(web::http::http_response response)
{
    if (response.status_code() == web::http::status_codes::OK)
    {
        //TODO: Colocar na GUI
        std::cout << "Conseguiu remover stock" << std::endl;
        this->_quotes.erase(this->_ticker_to_remove);
        this->_ticker_to_remove = "";
    }
    else if(response.status_code() == web::http::status_codes::NotFound)
    {
        //TODO: Colocar mensagem na gui
        std::cout << "Não conseguiu remover stock" << std::endl;
        // this->_login_gui->showError();
    }
}

void Client::removeStockFromQuotes(std::string ticker)
{
    this->_ticker_to_remove = ticker;
    web::http::client::http_client remove_quote(this->_quote + "?client_name=" + this->_client_name + "&ticker=" + ticker);
    auto putvalue = web::json::value::object();
    make_request_without_json_response(remove_quote, web::http::methods::DEL, putvalue, std::bind(&Client::_deleteStockCallback, this, std::placeholders::_1));
}

void Client::_getStockCallback(web::http::http_response response, web::json::value const &jvalue)
{
    if (response.status_code() == web::http::status_codes::OK)
    {
        //TODO: Colocar na GUI
        display_json(jvalue, "Conseguiu pegar stock: ");
        for (auto object = jvalue.as_object().cbegin(); object != jvalue.as_object().cend(); ++object)
        {
            const std::string &key = object->first;
            double value = object->second.as_double();
            this->_quotes[key] = value;

            std::cout << "key: " << key << ", value: " << value << std::endl;
        }
    }
    else if(response.status_code() == web::http::status_codes::NotFound)
    {
        //TODO: Colocar mensagem na gui
        std::cout << "Não conseguiu pegar stock" << std::endl;
        // this->_login_gui->showError();
    }
}

void Client::getCurrentQuotes()
{
    web::http::client::http_client get_quote(this->_quote + "?client_name=" + this->_client_name);
    auto putvalue = web::json::value::object();
    make_request_with_json_response(get_quote, web::http::methods::GET, putvalue, std::bind(&Client::_getStockCallback, this, std::placeholders::_1, std::placeholders::_2));
}

void Client::_createOrderCallback(web::http::http_response response)
{
    if (response.status_code() == web::http::status_codes::OK)
    {
        //TODO: Colocar na GUI
        std::cout << "Conseguiu criar a ordem" << std::endl;
    }
    else if(response.status_code() == web::http::status_codes::BadRequest)
    {
        //TODO: Colocar mensagem na gui
        std::cout << "Não conseguiu criar a ordem pq expirou" << std::endl;
        // this->_login_gui->showError();
    }
    else if(response.status_code() == web::http::status_codes::Forbidden)
    {
        //TODO: Colocar mensagem na gui
        std::cout << "Não conseguiu criar a ordem pq não tem o sufuciente" << std::endl;
        // this->_login_gui->showError();
    }
    else if(response.status_code() == web::http::status_codes::NotFound)
    {
        //TODO: Colocar mensagem na gui
        std::cout << "Não conseguiu criar a ordem pq não achou parametros" << std::endl;
        // this->_login_gui->showError();
    }
}

void Client::createOrder(OrderType order_type,
                        std::string ticker, 
                        double amount,
                        double price,
                        time_t expiration_datetime)
{
    std::string expiration_datetime_string = time_to_string(&expiration_datetime);
    web::http::client::http_client create_order(this->_order);
    Order order_obj(this->_client_name, order_type, ticker, amount, price, expiration_datetime_string);
    web::json::value order_json = order_obj.toJson();
    make_request_without_json_response(create_order, web::http::methods::POST, order_json, std::bind(&Client::_createOrderCallback, this, std::placeholders::_1));
}