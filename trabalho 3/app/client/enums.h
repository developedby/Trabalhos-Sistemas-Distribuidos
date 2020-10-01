#ifndef ENUMS_H
#define ENUMS_H

#include <string>

enum class OrderType 
{
    BUY,
    SELL
};

enum class HomebrokerErrorCode
{
    SUCCESS,
    FORBIDDEN_NAME,
    NOT_ENOUGH_STOCK,
    UNKNOWN_TICKER
};

static OrderType get_matching(OrderType type)
{
    if (type == OrderType::BUY)
    {
        return OrderType::SELL;
    }
    else if (type == OrderType::SELL)
    {
        return OrderType::BUY;    
    }

    return OrderType::BUY;
}

static std::string enum_to_string(OrderType type)
{
    if (type == OrderType::BUY)
    {
        return "BuyOrder";
    }
    else if (type == OrderType::SELL)
    {
        return "SellOrder";
    }
    
    return "";
}

static OrderType string_to_enum(std::string type_string)
{
    if (type_string == "BuyOrder")
    {
        return OrderType::BUY;
    }
    else if (type_string == "SellOrder")
    {
        return OrderType::SELL;
    }
    
    return OrderType::BUY;
}


#endif