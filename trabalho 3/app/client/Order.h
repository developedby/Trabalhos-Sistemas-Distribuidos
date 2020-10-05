#ifndef ORDER_H
#define ORDER_H

#include "enums.h"
#include <string>
#include <cpprest/json.h>

std::string time_to_string(time_t *timestamp);

class Order
{
    bool _active;
public:
    std::string client_name;
    OrderType type;
    std::string ticker;
    double amount;
    double price;
    std::string expiry_date;

    Order(std::string client_name_, OrderType type_, std::string ticker_, double amount_, double price_, std::string expiry_date_, bool active_ = true);
    Order()
    {

    }
    web::json::value toJson();
    static Order fromJson(web::json::value &order_json);
    bool operator==(const Order &order_to_compare);
};

class Transaction
{
public:
    std::string ticker;
    std::string seller_name;
    std::string buyer_name;
    double amount;
    double price;
    std::string datetime;

    Transaction(std::string ticker_, std::string seller_name_, std::string buyer_name_, double amount_, double price_, std::string datetime_);
    web::json::value toJson();
    static Transaction fromJson(web::json::value &transaction_json);
};

#endif