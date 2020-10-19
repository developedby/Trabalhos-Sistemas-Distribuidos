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

    /** Cria Ordem - Uma classe que representa uma ordem
     *
     *  @param client_name_         Nome do cliente
     *  @param type_                Tipo da ordem
     *  @param ticker_              Nome da ação
     *  @param amount_              Quantidade a ser negociada
     *  @param expiry_date_         Tempo limite por qual a ordem estará ativa (string)
     *  @param active_              true se a ordem está ativa, falsa caso contrário. Default: true
     */
    Order(std::string client_name_, OrderType type_, std::string ticker_, double amount_, double price_, std::string expiry_date_, bool active_ = true);

    /** Cria Ordem - Uma classe que representa uma ordem. 
     *  Construtor usado para inicialização da classe se necessário
     */
    Order()
    {

    }

    /** Transforma os dados da classe num json
     * 
     *  @return                     JSON final
     */
    web::json::value toJson();

    /** Cria uma Order a partir de um json
     *  
     *  @param order_json           Json contendo uma representação da classe
     *  @return                     Objeto final
     */
    static Order fromJson(web::json::value &order_json);

    /** Compara os dados da classe com uma Order externa
     *  
     *  @param order_to_compare     Order para ser comparada
     *  @return                     true se as orders forem iguais, false caso contrário
     */
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

    /** Cria Transaction - Uma classe que representa uma transação
     *
     *  @param ticker_              Nome da ação
     *  @param seller_name_         Nome do vendedor
     *  @param buyer_name_          Nome do comprador
     *  @param amount_              Quantidade negociada
     *  @param price_               Preço negociado
     *  @param datetime_            Data que a transação foi executada
     */
    Transaction(std::string ticker_, std::string seller_name_, std::string buyer_name_, double amount_, double price_, std::string datetime_);

    /** Transforma os dados da classe num json
     * 
     *  @return                     JSON final
     */
    web::json::value toJson();

    /** Cria uma Transaction a partir de um json
     *  
     *  @param transaction_json     Json contendo uma representação da classe
     *  @return                     Objeto final
     */
    static Transaction fromJson(web::json::value &transaction_json);
};

#endif