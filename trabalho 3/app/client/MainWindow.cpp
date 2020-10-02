#include "MainWindow.h"
#include "gui.h"
#include "Client.h"
#include <iostream>
#include <string>
#include <ctime>


MainWindow::MainWindow(Client &client_) : QMainWindow(), _ui(Ui::MainWindow()), _client(client_)
{
    this->_ui.setupUi(this);
    connect(this->_ui.add_quote_btn, SIGNAL(released()), this, SLOT(_onAddQuoteBtn()));
    connect(this->_ui.remove_quote_btn, SIGNAL(released()), this, SLOT(_onRemoveQuoteBtn()));
    connect(this->_ui.add_alert_btn, SIGNAL(released()), this, SLOT(_onAddAlertBtn()));
    connect(this->_ui.create_order_btn, SIGNAL(released()), this, SLOT(_onCreateOrderBtn()));
    connect(this->_ui.update_btn, SIGNAL(released()), this, SLOT(_onUpdateBtn()));
}

void MainWindow::_onAddQuoteBtn()
{
    const std::string quote_name = this->_ui.quote_name->text().toUtf8().constData();

    if (quote_name.empty())
    {
        std::cout << "Valores inválidos" << std::endl;
        return;
    }

    std::cout << "Botao clicado onAddQuoteBtn" << std::endl;
    std::cout << "Colocou o nome " << quote_name << std::endl;

    // const bool error = this->_client.addStockToQuotes(ticker);
    bool error = false;
    if (!error)
    {
        this->_ui.quote_name->clear();
    }
}

void MainWindow::_onRemoveQuoteBtn()
{
    const std::string ticker = this->_ui.quote_name->text().toUtf8().constData();

    if (ticker.empty())
    {
        std::cout << "Valores inválidos" << std::endl;
        return;
    }
    
    std::cout << "Botao clicado _onRemoveQuoteBtn" << std::endl;
    std::cout << "Colocou o nome " << ticker << std::endl;

    // const bool error = this->_client.removeStockFromQuotes(ticker);
    bool error = false;
    if (!error)
    {
        this->_ui.quote_name->clear();
    }
}

void MainWindow::_onAddAlertBtn()
{
    const std::string ticker = this->_ui.alert_quote->text().toUtf8().constData();
    bool ok[2];
    float stub[2];
    stub[0] = this->_ui.alert_price_low->text().toFloat(&ok[0]);
    stub[1] = this->_ui.alert_price_high->text().toFloat(&ok[1]);

    float low_price = -1;
    float high_price = -1;

    if (ok[0] && ok[1])
    {
        low_price = stub[0];
        high_price = stub[1];
    }
    if (low_price < 0 || high_price < 0 || ticker.empty())
    {
        std::cout << "Valores inválidos" << std::endl;   
    }
    
    std::cout << "Botao clicado _onAddAlertBtn" << std::endl;
    std::cout << "Nome: " << ticker << ", limite baixo: " << low_price << ", limite alto: " << high_price << std::endl;

    // const bool error = this->_client.addQuoteAlert(ticker, low_price, high_price);
    bool error = false;
    if (!error)
    {
        this->_ui.alert_quote->clear();
        this->_ui.alert_price_low->clear();
        this->_ui.alert_price_high->clear();
    }

}

void MainWindow::_onCreateOrderBtn()
{
    const std::string ticker = this->_ui.order_name->text().toUtf8().constData();
    bool ok[3];
    float stub[3];

    stub[0] = this->_ui.order_amount->text().toFloat(&ok[0]);
    stub[1] = this->_ui.order_price->text().toFloat(&ok[1]);
    stub[2] = this->_ui.order_expiration->text().toFloat(&ok[2]);

    bool sell_order = this->_ui.sell_order->isChecked();
    bool buy_order = this->_ui.buy_order->isChecked();

    float amount = -1;
    float price = -1;
    float expiration_minutes = -1;
    if (ok[0] && ok[1] && ok[2])
    {
        amount = stub[0];
        price = stub[1];
        expiration_minutes = stub[2];
    }
    

    if (amount < 0 || price < 0 || expiration_minutes < 0 || (!sell_order && !buy_order) || ticker.empty())
    {
        std::cout << "Valores inválidos" << std::endl;  
        return; 
    }

    const OrderType order_type = buy_order ? OrderType::BUY : OrderType::SELL;

    const time_t expiration_datetime = time(NULL) + int(expiration_minutes * 60);

    std::cout << "Botao clicado _onCreateOrderBtn" << std::endl;
    std::cout << "Nome: " << ticker << ", quantidade: " << amount << ", valor: " << price << ", time: " << ctime(&expiration_datetime) << ", compra: " << buy_order << ", venda: " << sell_order << std::endl;

    // const bool error = this->_client.createOrder(order_type, ticker, amount, price, expiration_datetime)
    bool error = false;
    if (!error)
    {
        this->_ui.order_name->clear();
        this->_ui.order_amount->clear();
        this->_ui.order_price->clear();
        this->_ui.order_expiration->clear();
    }
}

void MainWindow::_onUpdateBtn()
{
    std::cout << "Botao clicado _onUpdateBtn" << std::endl;
    // this->_client.getCurrentQuotes();
}
