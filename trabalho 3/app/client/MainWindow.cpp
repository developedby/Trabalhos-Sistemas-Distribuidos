#include "MainWindow.h"
#include "gui.h"
#include "Client.h"
#include <iostream>
#include <string>
#include <ctime>
#include "Order.h"
#include "enums.h"


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
    const std::string ticker = this->_ui.quote_name->text().toUtf8().constData();

    if (ticker.empty())
    {
        std::cout << "Valores inválidos" << std::endl;
        return;
    }

    this->_client.addStockToQuotes(ticker);
}

void MainWindow::_onRemoveQuoteBtn()
{
    const std::string ticker = this->_ui.quote_name->text().toUtf8().constData();

    if (ticker.empty())
    {
        std::cout << "Valores inválidos" << std::endl;
        return;
    }
    this->_client.removeStockFromQuotes(ticker);
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
    QList<QTableWidgetItem *> results = this->_ui.quote_table->findItems(QString::fromStdString(ticker), Qt::MatchExactly);
    if (low_price < 0 || high_price < 0 || ticker.empty() || results.size() <= 0)
    {
        std::cout << "Valores inválidos" << std::endl;  
        return; 
    }
    
    this->_client.addQuoteAlert(ticker, low_price, high_price);

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

    this->_client.createOrder(order_type, ticker, amount, price, expiration_datetime);
}

void MainWindow::_onUpdateBtn()
{
    this->_client.getCurrentQuotes();
}

void MainWindow::updateQuotes(std::map<std::string, double> quotes)
{
    for(auto &quote:quotes)
    {
        QList<QTableWidgetItem *> results = this->_ui.quote_table->findItems(QString::fromStdString(quote.first), Qt::MatchExactly);
        int row = -1;
        if (results.size() <= 0)
        {
            row = this->_ui.quote_table->rowCount();
            this->_ui.quote_table->insertRow(row);
            this->_ui.quote_table->setItem(row, 0, new QTableWidgetItem(QString::fromStdString(quote.first)));
            this->_ui.quote_table->setItem(row, 1, new QTableWidgetItem(QString::number(quote.second)));
            this->_ui.quote_table->setItem(row, 2, new QTableWidgetItem(""));
        }
        else
        {
            row = this->_ui.quote_table->row(results[0]);
            QTableWidgetItem *item = this->_ui.quote_table->item(row, 1);
            item->setText(QString::number(quote.second));
        }
    }
    this->_ui.quote_table->viewport()->update();
}

void MainWindow::removeQuotes(std::string ticker)
{
    QList<QTableWidgetItem *> results = this->_ui.quote_table->findItems(QString::fromStdString(ticker), Qt::MatchExactly);
    if (results.size() > 0)
    {
        int row = this->_ui.quote_table->row(results[0]);
        this->_ui.quote_table->removeRow(row);
    }
    this->_ui.quote_table->viewport()->update();
}

void MainWindow::clearQuoteAction()
{
    this->_ui.quote_name->setText("");
}

void MainWindow::updateAlerts(std::map<std::string, std::pair<double, double>> alerts)
{
    for(auto &alert:alerts)
    {
        QList<QTableWidgetItem *> results = this->_ui.quote_table->findItems(QString::fromStdString(alert.first), Qt::MatchExactly);
        if (results.size() > 0)
        {
            int row = this->_ui.quote_table->row(results[0]);
            QTableWidgetItem *item = this->_ui.quote_table->item(row, 2);
            QString alert_string = "(" + QString::number(alert.second.first) + ", " + QString::number(alert.second.second) + ")";
            item->setText(alert_string);
            this->_ui.quote_table->viewport()->update();
        }
    }
}

void MainWindow::clearAlertAction()
{
    this->_ui.alert_quote->clear();
    this->_ui.alert_price_low->clear();
    this->_ui.alert_price_high->clear();
}

void MainWindow::removeAlert(std::string ticker)
{
    QList<QTableWidgetItem *> results = this->_ui.quote_table->findItems(QString::fromStdString(ticker), Qt::MatchExactly);
    if (results.size() > 0)
    {
        int row = this->_ui.quote_table->row(results[0]);
        QTableWidgetItem *item = this->_ui.quote_table->item(row, 2);
        item->setText("");
        this->_ui.quote_table->viewport()->update();
    }
}

void MainWindow::addMessage(std::string msg)
{
    time_t timestamp = time(NULL);
    std::string timestamp_string = time_to_string(&timestamp);
    QString final_string = QString::fromStdString(timestamp_string) + ": " + QString::fromStdString(msg) + '\n';
    this->_ui.messages->setReadOnly(false);
    this->_ui.messages->insertPlainText(final_string);
}

void MainWindow::clearOrderAction()
{
    this->_ui.order_name->clear();
    this->_ui.order_amount->clear();
    this->_ui.order_price->clear();
    this->_ui.order_expiration->clear();
}

void MainWindow::updateOrders(std::vector<Order> orders)
{
    while(this->_ui.order_table->rowCount())
    {
        this->_ui.order_table->removeRow(0);
    }

    for (auto order:orders)
    {
        int row = this->_ui.order_table->rowCount();
        this->_ui.order_table->insertRow(row);
        this->_ui.order_table->setItem(row, 0, new QTableWidgetItem(QString::fromStdString(order.ticker)));
        this->_ui.order_table->setItem(row, 1, new QTableWidgetItem(QString::number(order.price)));
        this->_ui.order_table->setItem(row, 2, new QTableWidgetItem(QString::number(order.amount)));
        this->_ui.order_table->setItem(row, 3, new QTableWidgetItem(QString::fromStdString(enum_to_string_portuguese(order.type))));
        this->_ui.order_table->setItem(row, 4, new QTableWidgetItem(QString::fromStdString(order.expiry_date)));
    }
}

void MainWindow::updateOwnQuotes(std::map<std::string, std::pair<double, double>> own_stocks)
{
    while(this->_ui.own_stock_table->rowCount())
    {
        this->_ui.own_stock_table->removeRow(0);
    }

    for (auto own_stock:own_stocks)
    {
        int row = this->_ui.own_stock_table->rowCount();
        this->_ui.own_stock_table->insertRow(row);
        this->_ui.own_stock_table->setItem(row, 0, new QTableWidgetItem(QString::fromStdString(own_stock.first)));
        this->_ui.own_stock_table->setItem(row, 1, new QTableWidgetItem(QString::number(own_stock.second.first)));
        this->_ui.own_stock_table->setItem(row, 2, new QTableWidgetItem(QString::number(own_stock.second.second)));
    }
}