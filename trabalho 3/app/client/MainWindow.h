#ifndef MY_MAIN_WINDOW_H 
#define MY_MAIN_WINDOW_H

#include "gui.h"
#include "Client.h"

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
    // void show();
    // void close();

};

#endif