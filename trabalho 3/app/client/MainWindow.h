#ifndef MY_MAIN_WINDOW_H 
#define MY_MAIN_WINDOW_H

#include "gui.h"
#include "Client.h"
#include "Order.h"

class MainWindow : public QMainWindow
{
    Q_OBJECT
    Ui::MainWindow _ui;
    Client &_client;

private slots:
    void _onAddQuoteBtn();
    void _onRemoveQuoteBtn();
    void _onAddAlertBtn();
    void _onCreateOrderBtn();
    void _onUpdateBtn();
    
public:
    MainWindow(Client &client_);
    void updateQuotes(std::map<std::string, double> quotes);
    void clearQuoteAction();
    void updateAlerts(std::map<std::string, std::pair<double, double>> alerts);
    void clearAlertAction();
    void removeQuotes(std::string ticker);
    void removeAlert(std::string ticker);
    void addMessage(std::string msg, bool error = false);
    void clearOrderAction();
    void updateOrders(std::vector<Order> orders);
    void updateOwnedQuotes(std::map<std::string, std::pair<double, double>> owned_stocks);
    void closeEvent( QCloseEvent* event );

signals:
    void showMainWindowSignal();

};

#endif