#ifndef MY_MAIN_WINDOW_H 
#define MY_MAIN_WINDOW_H

#include "gui.h"
#include "Client.h"
#include "Order.h"

class MainWindow : public QMainWindow
{
    Q_OBJECT
    Ui::MainWindow _ui; //janela
    Client &_client; //Referênca de cliente

private slots:

//Callback de botões
    /** Pega os valores da janela para adicionar uma ação e chama Client::addStockToQuotes
     *  Caso tenha um erro, chama addMessage
     */
    void _onAddQuoteBtn();

    /** Pega os valores da janela para remover uma ação e chama Client::removeStockFromQuotes
     *  Caso tenha um erro, chama addMessage
     */
    void _onRemoveQuoteBtn();

    /** Pega os valores da janela para adicionar um alerta e chama Client::addQuoteAlert
     *  Caso tenha um erro, chama addMessage
     */
    void _onAddAlertBtn();

    /** Pega os valores da janela para adicionar uma ordem  e chama Client::createOrder
     *  Caso tenha um erro, chama addMessage
     */
    void _onCreateOrderBtn();

    /** Chama Client::getCurrentQuotes
     */
    void _onUpdateBtn();
    
public:
    /** Cria MainWindow - uma classe para interfacear com a janela principal
     *  Também vai conectar os botões para as funções em private slots
     *
     *  @param client_                  Referência para a classe Cliente
     */
    MainWindow(Client &client_);

    /** Atualiza as ações na janela.
     *
     *  @param quotes                   Ações para ser colocada na janela
     */
    void updateQuotes(std::map<std::string, double> quotes);

    /** Limpa as entradas do usuário para ações de ação
     */
    void clearQuoteAction();

    /** Atualiza os alertas na janela.
     *
     *  @param alerts                   Alertas para serem incluídos
     */
    void updateAlerts(std::map<std::string, std::pair<double, double>> alerts);

    /** Limpa as entradas do usuário para ações de alerta
     */
    void clearAlertAction();

    /** Remove uma ação da janela.
     *
     *  @param ticker                   Nome da ação para ser removida
     */
    void removeQuotes(std::string ticker);

    /** Remove um alerta da janela.
     *
     *  @param ticker                   Nome da ação do alerta para ser removido
     */
    void removeAlert(std::string ticker);

    /** Adiciona uma mensagem na janela. No início de cada mensagem, vai colocar o horário atual
     *
     *  @param msg                      Mensagem para ser inserida
     *  @param error                    true se for uma mensagem de erro, false caso contrário. Default: false
     */
    void addMessage(std::string msg, bool error = false);

    /** Limpa as entradas do usuário para ações de ordem
     */
    void clearOrderAction();

    /** Atualiza as ordens na janela
     *
     *  @param orders                   Ordens para serem mostradas
     */
    void updateOrders(std::vector<Order> orders);

    /** Atualiza a carteira na janela
     *
     *  @param owned_stocks             Ações da carteira para serem mostradas
     */
    void updateOwnedQuotes(std::map<std::string, std::pair<double, double>> owned_stocks);

    /** Sobreposição do evento de fechar a janela. Vai chamar o Client::close
     *
     *  @param event                    Identificação do evento
     */
    void closeEvent( QCloseEvent* event );

signals:
    /** Sinal usado para mostrar a janela. Vai chamar show
     */
    void showMainWindowSignal();

};

#endif