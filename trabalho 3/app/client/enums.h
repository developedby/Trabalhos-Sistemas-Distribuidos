#ifndef ENUMS_H
#define ENUMS_H

#include <string>

//Enum com os possíveis tipos de ordem
enum class OrderType 
{
    BUY,
    SELL
};

/** Pega o correspondente do tipo da ordem (compra->venda e vice e versa)
 *  
 *  @param type                 Tipo da ordem
 *  @return                     Ordem oposta
 */
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

/** Pega a string que define uma ordem
 *  
 *  @param type                 Tipo da ordem
 *  @return                     String com a resposta
 */
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

/** Cria uma OrderType a partir de uma string
 *  
 *  @param type_string          String que corresponde à OrderType
 *  @return                     OrderType
 */
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

/** Pega a string em português que define uma ordem
 *  
 *  @param type                 Tipo da ordem
 *  @return                     String com a resposta
 */
static std::string enum_to_string_portuguese(OrderType type)
{
    if (type == OrderType::BUY)
    {
        return "Ordem de compra";
    }
    else if (type == OrderType::SELL)
    {
        return "Ordem de venda";
    }
    
    return "";
}

#endif