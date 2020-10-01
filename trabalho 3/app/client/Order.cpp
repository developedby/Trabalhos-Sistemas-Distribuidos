#include "Order.h"
#include "enums.h"
#include <string>
#include <cpprest/json.h>
#pragma comment(lib, "cpprest_2_10")

Order::Order(std::string client_name_, OrderType type_, std::string ticker_, double amount_, double price_, time_t expiry_date_, bool active_)
{
    client_name = client_name_;
    type = type_;
    ticker = ticker_;
    amount = amount_;
    price = price_;
    expiry_date = expiry_date_;
    _active = active_;
}

web::json::value Order::toJson()
{
    auto order_json = web::json::value::object();
    order_json["client_name"] = web::json::value::string(this->client_name);
    order_json["type"] = web::json::value::string(enum_to_string(this->type));
    order_json["ticker"] = web::json::value::string(this->ticker);
    order_json["amount"] = web::json::value::number(this->amount);
    order_json["price"] = web::json::value::number(this->price);
    order_json["expiry_date"] = web::json::value::number(this->expiry_date);
    order_json["active"] = web::json::value::boolean(this->_active);

    return order_json;
}

Order Order::fromJson(web::json::value &order_json)
{   
    return Order(
        order_json["client_name"].as_string(), 
        string_to_enum(order_json["type"].as_string()), 
        order_json["ticker"].as_string(), 
        order_json["amount"].as_double(), 
        order_json["price"].as_double(), 
        time_t(order_json["expiry_date"].as_integer()), 
        order_json["active"].as_bool());
}

Transaction::Transaction(std::string ticker_, std::string seller_name_, std::string buyer_name_, double amount_, double price_, time_t datetime_)
{
    ticker = ticker_;
    seller_name = seller_name_;
    buyer_name = buyer_name_;
    amount = amount_;
    price = price_;
    datetime = datetime_;
}

web::json::value Transaction::toJson()
{
    auto transaction_json = web::json::value::object();

    transaction_json["ticker"] = web::json::value::string(this->ticker);
    transaction_json["seller_name"] = web::json::value::string(this->seller_name);
    transaction_json["buyer_name"] = web::json::value::string(this->buyer_name);
    transaction_json["amount"] = web::json::value::number(this->amount);
    transaction_json["price"] = web::json::value::number(this->price);
    transaction_json["datetime"] = web::json::value::number(this->datetime);

    return transaction_json;
}

Transaction Transaction::fromJson(web::json::value &transaction_json)
{
    return Transaction(
        transaction_json["ticker"].as_string(), 
        transaction_json["seller_name"].as_string(), 
        transaction_json["buyer_name"].as_string(), 
        transaction_json["amount"].as_double(), 
        transaction_json["price"].as_double(), 
        time_t(transaction_json["datetime"].as_integer()));
}