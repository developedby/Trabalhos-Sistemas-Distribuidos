#ifndef ORDER_H
#define ORDER_H

#include "enums.h"
#include <string>
#include <cpprest/json.h>

class Order
{
    bool _active;
public:
    std::string client_name;
    OrderType type;
    std::string ticker;
    double amount;
    double price;
    time_t expiry_date;

    Order(std::string client_name_, OrderType type_, std::string ticker_, double amount_, double price_, time_t expiry_date_, bool active_ = true);
    web::json::value toJson();
    Order fromJson(web::json::value &order_json);
};

class Transaction
{
public:
    std::string ticker;
    std::string seller_name;
    std::string buyer_name;
    double amount;
    double price;
    time_t datetime;

    Transaction(std::string ticker_, std::string seller_name_, std::string buyer_name_, double amount_, double price_, time_t datetime_);
    web::json::value toJson();
    Transaction fromJson(web::json::value &transaction_json);
};

#endif