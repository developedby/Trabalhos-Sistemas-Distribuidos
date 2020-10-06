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
    std::vector<Order> _active_orders; //active orders
    std::map<std::string, std::pair<double, double>> _alerts; //ticker->(lower_limit, upper_limit)
    LoginEvent *_events; //Thread de eventos do sse
    MainWindow *_gui; //Janela principal, abre depois que é feito o login
    ClientLoginWindow *_login_gui; //Janela de login

    //Variaveis para se comunicar entre callbacks
    Order _last_order;
    std::string _client_name;
    std::string _ticker_to_remove;
    std::string _alert_ticker;
    bool _connection_closed;

    //URLs para se comunicar com o servidor
    std::string _login_url;
    std::string _status_url;
    std::string _order_url;
    std::string _limit_url;
    std::string _quote_url;
    std::string _close_url;    

    /** Callback que pode ser usada para fazer login, caso não se use sse.
     *  Irá verificar a resposta, se der erro vai mostrar a mensagem de erro na janela de login
     *  Se der certo, vai fechar a janela de login e abrir a janela principal
     * 
     *  @param response             Resposta HTTP
     */
    void _loginCallback(web::http::http_response response);

    /** Callback que trata a resposta da requisição de addStockToQuotes
     *  Caso dê certo, irá chamar getCurrentQuotes. Caso contrário, vai mostrar uma mensagem de erro na gui
     * 
     *  @param response             Resposta HTTP
     */
    void _addStockCallback(web::http::http_response response);

    /** Callback que trata a resposta da requisição de removeStockFromQuotes
     *  Caso dê certo, irá chamar getCurrentQuotes. Caso contrário, vai mostrar uma mensagem de erro na gui
     * 
     *  @param response             Resposta HTTP
     */
    void _removeStockCallback(web::http::http_response response);

    /** Callback que trata a resposta da requisição de getCurrentQuotes
     *  Caso dê certo, irá chamar atualizar o valor das ações monitoradas e o valor da carteira. 
     *  Caso contrário, vai mostrar uma mensagem de erro na gui
     * 
     *  @param response             Resposta HTTP
     *  @param jvalue               Resposta json do servidor
     */
    void _getStockCallback(web::http::http_response response, web::json::value const &jvalue);

    /** Callback que trata a resposta da requisição de createOrder
     *  Caso dê certo, irá colocar a ordem na gui. Caso contrário, vai mostrar uma mensagem de erro na gui
     * 
     *  @param response             Resposta HTTP
     */
    void _createOrderCallback(web::http::http_response response);

    /** Callback que trata a resposta da requisição de addQuoteAlert
     *  Caso dê certo, irá colocar os limites do alerta na gui. Caso contrário, vai mostrar uma mensagem de erro na gui
     * 
     *  @param response             Resposta HTTP
     */
    void _addAlertCallback(web::http::http_response response);

    /** Callback que trata a resposta da requisição de getState
     *  Caso dê certo, irá atualizar as ações, alertas, ordens e carteira na gui
     * 
     *  @param response             Resposta HTTP
     *  @param jvalue               Resposta json do servidor
     */
    void _getStateCallback(web::http::http_response response, web::json::value const &jvalue);

    /** Callback que trata a resposta da requisição de close
     *  Independente da resposta, irá fechar a janela e o programa
     * 
     *  @param response             Resposta HTTP
     */
    void _closeCallback(web::http::http_response response);

    /** Função que faz requisição HTTP para um servidor que não tem um json como resposta
     *  Caso o servidor não esteja disponível, fechará o programa
     * 
     *  @param client               URL HTTP da requisição
     *  @param mtd                  Método HTTP da requisição
     *  @param jvalue               JSON para mandar para o servidor. Se não tem json na requisição, mandar vazio
     *  @param callback_func        Função que será chamada quando a resposta da requisição chegar. Essa função deve receber a resposta http como argumento
     */
    friend void make_request_without_json_response(web::http::client::http_client & client, web::http::method mtd, web::json::value const &jvalue, 
                                        std::function<void(web::http::http_response response)> callback_func);

    /** Função que faz requisição HTTP para um servidor que tem um json como resposta
     *  Caso o servidor não esteja disponível, fechará o programa
     *  @param client               URL HTTP da requisição
     *  @param mtd                  Método HTTP da requisição
     *  @param jvalue               JSON para mandar para o servidor. Se não tem json na requisição, mandar vazio
     *  @param callback_func        Função que será chamada quando a resposta da requisição chegar. Essa função deve receber a resposta http e o json como argumento
     */
    friend void make_request_with_json_response(web::http::client::http_client & client, web::http::method mtd, web::json::value const &jvalue, 
                                    std::function<void(web::http::http_response response, web::json::value const &jvalue)> callback_func);
    
public:
    ClientConnectionStatus connection_status; //Setado para dizer se está conectado ou não

    /** Cria Client - Uma classe que serve como cliente e se comunica com um servidor usando REST.
     *  Irá criar os objetos (exceto _events) e vai mostrar a janela de login
     *  Irá também linkar os sinais showLoginErrorSignal, closeLoginWindowSignal e showMainWindowSignal;
     *
     *  @param uri                  URI do servidor (url inicial + porta)
     */
    Client(std::string uri);

    /** Cria uma ordem de compra ou venda. Vai mandar uma ordem para o servidor. 
     *  A resposta é tratada em _createOrderCallback
     *
     *  @param order_type           Tipo da ordem (compra ou venda)
     *  @param ticker               Nome da ação
     *  @param amount               Quantidade de ações para ser negociada
     *  @param price                Valor que se está disposto a executar a transação
     *  @param expiration_datetime  Tempo limite por qual a ordem estará ativa
     */
    void createOrder(OrderType order_type,
                     std::string ticker, 
                     double amount,
                     double price,
                     time_t expiration_datetime);

    /** Adiciona alerta para uma ação. Var mandar um alerta para o servidor. 
     *  A resposta é tratada em _addAlertCallback
     *
     *  @param ticker               Nome da ação
     *  @param lower_limit          Valor mais baixo para ser considerado. Se a ação estiver abaixo desse valor o servidor gera um alerta
     *  @param upper_limit          Valor mais alto para ser considerado. Se a ação estiver acima desse valor o servidor gera um alerta
     */
    void addQuoteAlert(std::string ticker,
                       double lower_limit,
                       double upper_limit);
    
    /** Adiciona uma ação para a lista de ações de interesse. Var mandar uma ação para o servidor. 
     *  A resposta é tratada em _addStockCallback
     *
     *  @param ticker               Nome da ação
     */
    void addStockToQuotes(std::string ticker);

    /** Remove uma ação da lista de ações de interesse. Var mandar uma ação para o servidor. 
     *  A resposta é tratada em _removeStockCallback
     *
     *  @param ticker               Nome da ação
     */
    void removeStockFromQuotes(std::string ticker);

    /** Atualiza o valor das ações de interesse. Vai manda uma requisição para o servidor. 
     *  A resposta é tratada em _getStockCallback
     */
    void getCurrentQuotes();

    /** Notifica que um alerta foi resolvido. É chamado quando tem um evento de limite por parte do sse. 
     *  Vai remover o alerta da gui e colocar uma mensagem na gui
     *
     *  @param ticker               Nome da ação
     *  @param current_quote        Valor atual da ação
     */
    void notifyLimit(std::string ticker, double current_quote);

    /** Notifica que uma ordem foi executada. É chamado quando tem um evento de ordem por parte do sse. 
     *  Vai chamar getCurrentQuotes para pegar o valor atual das ações, e atualizar as ordem ativas e a carteira na gui
     *  Também irá colocar uma mensagem na gui para cada transação executada e cada ordem expirada
     *
     *  @param notification_json    Json com os dados do evento
     */
    void notifyOrder(web::json::value notification_json);

    /** Faz um pedido de login para o servidor. Isso irá criar uma conexão permanente com o servidor usando sse dentro de _events.
     *  A resposta é tratada na thread _events, assim como todos os outros eventos de sse
     *
     *  @param client_name          Nome do cliente
     */
    void login(std::string client_name);

    /** Pega o estado atual do cliente. Vai mandar uma requisição para o servidor.
     *  A resposta é tratada em _getStateCallback
     */
    void getState();

    /** Fecha a conexão com o servidor. Vai mandar uma requisição para o servidor.
     *  A resposta é tratada em _closeCallback
     */
    void close();

signals:
    /** Sinal usado para chamar ClientLoginWindow::showError
     */
    void showLoginErrorSignal();

    /** Sinal usado para chamar ClientLoginWindow::close
     */
    void closeLoginWindowSignal();

    /** Sinal usado para chamar MainWindow::show
     */
    void showMainWindowSignal();
};

class LoginEvent : public QThread
{
    Q_OBJECT
    Client &_client; //Referência para o cliente
    std::string _url; //URL de login

    /** Inicia a thread. Vai criar uma conexão http persistente com o servidor usando sse
     *  A resposta dos eventos é tratada em _eventsCallback
     */
    void run() override;

    /** Função que vai verificar os eventos sse
     *  Caso o evento seja de login, vai verificar se deu certo ou não. 
     *      Se deu certo chama Client::showMainWindowSignal e Client::closeLoginWindowSignal
     *      Se não, chama Client::showLoginErrorSignal
     *  Caso o evento seja de alerta, vai chamar Client::notifyLimit
     *  Caso o evento seja de ordem, vai chamar Client::notifyOrder
     * 
     *  @param result               Dados do evento
     */ 
    void _eventsCallback(std::string result);

public:
    /** Cria LoginEvent - Uma classe que serve como thread para captar os eventos sse.
     *  Irá criar os objetos (exceto _events) e vai mostrar a janela de login
     *
     *  @param client_              Referência para a classe de cliente
     *  @param url_                 URL para fazer login no servidor
     */
    LoginEvent(Client &client_, std::string url_);
};

#endif