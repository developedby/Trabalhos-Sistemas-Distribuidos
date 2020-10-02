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
    web::http::client::http_client login(this->_login + "?client_name=" + client_name);
    auto putvalue = web::json::value::object();
    make_request_without_json_response(login, web::http::methods::GET, putvalue, std::bind(&Client::_loginCallback, this, std::placeholders::_1));
}