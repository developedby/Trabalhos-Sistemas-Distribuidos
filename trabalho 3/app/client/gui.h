/********************************************************************************
** Form generated from reading UI file 'main_window.ui'
**
** Created by: Qt User Interface Compiler version 5.9.5
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_MAIN_WINDOW_H
#define UI_MAIN_WINDOW_H

#include <QtCore/QVariant>
#include <QtWidgets/QAction>
#include <QtWidgets/QApplication>
#include <QtWidgets/QButtonGroup>
#include <QtWidgets/QFrame>
#include <QtWidgets/QGridLayout>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QHeaderView>
#include <QtWidgets/QLabel>
#include <QtWidgets/QLineEdit>
#include <QtWidgets/QMainWindow>
#include <QtWidgets/QPlainTextEdit>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QRadioButton>
#include <QtWidgets/QTableWidget>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_MainWindow
{
public:
    QWidget *centralwidget;
    QGridLayout *gridLayout_13;
    QFrame *quote_group;
    QGridLayout *gridLayout_5;
    QGridLayout *gridLayout_2;
    QGridLayout *gridLayout;
    QLabel *quote_title;
    QPushButton *update_btn;
    QTableWidget *quote_table;
    QHBoxLayout *horizontalLayout;
    QGridLayout *gridLayout_3;
    QLabel *quote_action_title;
    QLabel *quote_add_title;
    QLineEdit *quote_name;
    QPushButton *add_quote_btn;
    QPushButton *remove_quote_btn;
    QGridLayout *gridLayout_4;
    QLabel *quote_alert_title;
    QLabel *alert_name_title;
    QLineEdit *alert_quote;
    QLabel *alert_price_low_title;
    QLineEdit *alert_price_low;
    QLabel *alert_max_price_title;
    QLineEdit *alert_price_high;
    QPushButton *add_alert_btn;
    QFrame *orders_group;
    QGridLayout *gridLayout_8;
    QGridLayout *gridLayout_6;
    QLabel *order_title;
    QTableWidget *order_table;
    QGridLayout *gridLayout_7;
    QLabel *create_order_title;
    QLabel *order_name_title;
    QLineEdit *order_name;
    QLabel *order_amount_title;
    QLineEdit *order_amount;
    QLabel *order_price_title;
    QLineEdit *order_price;
    QLabel *order_expiration_title;
    QLineEdit *order_expiration;
    QRadioButton *buy_order;
    QRadioButton *sell_order;
    QPushButton *create_order_btn;
    QFrame *owned_stock_group;
    QGridLayout *gridLayout_10;
    QGridLayout *gridLayout_9;
    QLabel *owned_stock_title;
    QTableWidget *owned_stock_table;
    QFrame *messages_group;
    QGridLayout *gridLayout_12;
    QGridLayout *gridLayout_11;
    QLabel *messages_title;
    QPlainTextEdit *messages;

    void setupUi(QMainWindow *MainWindow)
    {
        if (MainWindow->objectName().isEmpty())
            MainWindow->setObjectName(QStringLiteral("MainWindow"));
        MainWindow->resize(1280, 720);
        QSizePolicy sizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
        sizePolicy.setHorizontalStretch(0);
        sizePolicy.setVerticalStretch(0);
        sizePolicy.setHeightForWidth(MainWindow->sizePolicy().hasHeightForWidth());
        MainWindow->setSizePolicy(sizePolicy);
        centralwidget = new QWidget(MainWindow);
        centralwidget->setObjectName(QStringLiteral("centralwidget"));
        sizePolicy.setHeightForWidth(centralwidget->sizePolicy().hasHeightForWidth());
        centralwidget->setSizePolicy(sizePolicy);
        gridLayout_13 = new QGridLayout(centralwidget);
        gridLayout_13->setObjectName(QStringLiteral("gridLayout_13"));
        quote_group = new QFrame(centralwidget);
        quote_group->setObjectName(QStringLiteral("quote_group"));
        sizePolicy.setHeightForWidth(quote_group->sizePolicy().hasHeightForWidth());
        quote_group->setSizePolicy(sizePolicy);
        quote_group->setFrameShape(QFrame::Box);
        gridLayout_5 = new QGridLayout(quote_group);
        gridLayout_5->setObjectName(QStringLiteral("gridLayout_5"));
        gridLayout_2 = new QGridLayout();
        gridLayout_2->setObjectName(QStringLiteral("gridLayout_2"));
        gridLayout = new QGridLayout();
        gridLayout->setObjectName(QStringLiteral("gridLayout"));
        quote_title = new QLabel(quote_group);
        quote_title->setObjectName(QStringLiteral("quote_title"));
        sizePolicy.setHeightForWidth(quote_title->sizePolicy().hasHeightForWidth());
        quote_title->setSizePolicy(sizePolicy);
        quote_title->setAlignment(Qt::AlignCenter);

        gridLayout->addWidget(quote_title, 0, 0, 1, 1);

        update_btn = new QPushButton(quote_group);
        update_btn->setObjectName(QStringLiteral("update_btn"));
        QSizePolicy sizePolicy1(QSizePolicy::Minimum, QSizePolicy::Expanding);
        sizePolicy1.setHorizontalStretch(0);
        sizePolicy1.setVerticalStretch(0);
        sizePolicy1.setHeightForWidth(update_btn->sizePolicy().hasHeightForWidth());
        update_btn->setSizePolicy(sizePolicy1);

        gridLayout->addWidget(update_btn, 0, 1, 1, 1);


        gridLayout_2->addLayout(gridLayout, 0, 0, 1, 1);

        quote_table = new QTableWidget(quote_group);
        if (quote_table->columnCount() < 3)
            quote_table->setColumnCount(3);
        QTableWidgetItem *__qtablewidgetitem = new QTableWidgetItem();
        __qtablewidgetitem->setTextAlignment(Qt::AlignCenter);
        quote_table->setHorizontalHeaderItem(0, __qtablewidgetitem);
        QTableWidgetItem *__qtablewidgetitem1 = new QTableWidgetItem();
        __qtablewidgetitem1->setTextAlignment(Qt::AlignCenter);
        quote_table->setHorizontalHeaderItem(1, __qtablewidgetitem1);
        QTableWidgetItem *__qtablewidgetitem2 = new QTableWidgetItem();
        __qtablewidgetitem2->setTextAlignment(Qt::AlignCenter);
        quote_table->setHorizontalHeaderItem(2, __qtablewidgetitem2);
        quote_table->setObjectName(QStringLiteral("quote_table"));
        QSizePolicy sizePolicy2(QSizePolicy::Preferred, QSizePolicy::Preferred);
        sizePolicy2.setHorizontalStretch(0);
        sizePolicy2.setVerticalStretch(0);
        sizePolicy2.setHeightForWidth(quote_table->sizePolicy().hasHeightForWidth());
        quote_table->setSizePolicy(sizePolicy2);
        quote_table->horizontalHeader()->setCascadingSectionResizes(true);
        quote_table->horizontalHeader()->setDefaultSectionSize(201);
        quote_table->horizontalHeader()->setProperty("showSortIndicator", QVariant(true));
        quote_table->horizontalHeader()->setStretchLastSection(true);
        quote_table->verticalHeader()->setCascadingSectionResizes(true);
        quote_table->verticalHeader()->setProperty("showSortIndicator", QVariant(true));
        quote_table->verticalHeader()->setStretchLastSection(true);

        gridLayout_2->addWidget(quote_table, 1, 0, 1, 1);


        gridLayout_5->addLayout(gridLayout_2, 0, 0, 1, 1);

        horizontalLayout = new QHBoxLayout();
        horizontalLayout->setObjectName(QStringLiteral("horizontalLayout"));
        gridLayout_3 = new QGridLayout();
        gridLayout_3->setObjectName(QStringLiteral("gridLayout_3"));
        quote_action_title = new QLabel(quote_group);
        quote_action_title->setObjectName(QStringLiteral("quote_action_title"));
        sizePolicy.setHeightForWidth(quote_action_title->sizePolicy().hasHeightForWidth());
        quote_action_title->setSizePolicy(sizePolicy);
        quote_action_title->setAlignment(Qt::AlignCenter);

        gridLayout_3->addWidget(quote_action_title, 0, 0, 1, 1);

        quote_add_title = new QLabel(quote_group);
        quote_add_title->setObjectName(QStringLiteral("quote_add_title"));
        sizePolicy.setHeightForWidth(quote_add_title->sizePolicy().hasHeightForWidth());
        quote_add_title->setSizePolicy(sizePolicy);
        quote_add_title->setAlignment(Qt::AlignCenter);

        gridLayout_3->addWidget(quote_add_title, 1, 0, 1, 1);

        quote_name = new QLineEdit(quote_group);
        quote_name->setObjectName(QStringLiteral("quote_name"));
        sizePolicy.setHeightForWidth(quote_name->sizePolicy().hasHeightForWidth());
        quote_name->setSizePolicy(sizePolicy);

        gridLayout_3->addWidget(quote_name, 2, 0, 1, 1);

        add_quote_btn = new QPushButton(quote_group);
        add_quote_btn->setObjectName(QStringLiteral("add_quote_btn"));
        sizePolicy1.setHeightForWidth(add_quote_btn->sizePolicy().hasHeightForWidth());
        add_quote_btn->setSizePolicy(sizePolicy1);

        gridLayout_3->addWidget(add_quote_btn, 3, 0, 1, 1);

        remove_quote_btn = new QPushButton(quote_group);
        remove_quote_btn->setObjectName(QStringLiteral("remove_quote_btn"));
        sizePolicy.setHeightForWidth(remove_quote_btn->sizePolicy().hasHeightForWidth());
        remove_quote_btn->setSizePolicy(sizePolicy);

        gridLayout_3->addWidget(remove_quote_btn, 4, 0, 1, 1);


        horizontalLayout->addLayout(gridLayout_3);

        gridLayout_4 = new QGridLayout();
        gridLayout_4->setObjectName(QStringLiteral("gridLayout_4"));
        quote_alert_title = new QLabel(quote_group);
        quote_alert_title->setObjectName(QStringLiteral("quote_alert_title"));
        sizePolicy.setHeightForWidth(quote_alert_title->sizePolicy().hasHeightForWidth());
        quote_alert_title->setSizePolicy(sizePolicy);
        quote_alert_title->setAlignment(Qt::AlignCenter);

        gridLayout_4->addWidget(quote_alert_title, 0, 0, 1, 2);

        alert_name_title = new QLabel(quote_group);
        alert_name_title->setObjectName(QStringLiteral("alert_name_title"));
        sizePolicy.setHeightForWidth(alert_name_title->sizePolicy().hasHeightForWidth());
        alert_name_title->setSizePolicy(sizePolicy);
        alert_name_title->setAlignment(Qt::AlignCenter);

        gridLayout_4->addWidget(alert_name_title, 1, 0, 1, 1);

        alert_quote = new QLineEdit(quote_group);
        alert_quote->setObjectName(QStringLiteral("alert_quote"));
        sizePolicy.setHeightForWidth(alert_quote->sizePolicy().hasHeightForWidth());
        alert_quote->setSizePolicy(sizePolicy);

        gridLayout_4->addWidget(alert_quote, 1, 1, 1, 1);

        alert_price_low_title = new QLabel(quote_group);
        alert_price_low_title->setObjectName(QStringLiteral("alert_price_low_title"));
        sizePolicy.setHeightForWidth(alert_price_low_title->sizePolicy().hasHeightForWidth());
        alert_price_low_title->setSizePolicy(sizePolicy);
        alert_price_low_title->setAlignment(Qt::AlignCenter);

        gridLayout_4->addWidget(alert_price_low_title, 2, 0, 1, 1);

        alert_price_low = new QLineEdit(quote_group);
        alert_price_low->setObjectName(QStringLiteral("alert_price_low"));
        sizePolicy.setHeightForWidth(alert_price_low->sizePolicy().hasHeightForWidth());
        alert_price_low->setSizePolicy(sizePolicy);

        gridLayout_4->addWidget(alert_price_low, 2, 1, 1, 1);

        alert_max_price_title = new QLabel(quote_group);
        alert_max_price_title->setObjectName(QStringLiteral("alert_max_price_title"));
        sizePolicy.setHeightForWidth(alert_max_price_title->sizePolicy().hasHeightForWidth());
        alert_max_price_title->setSizePolicy(sizePolicy);
        alert_max_price_title->setAlignment(Qt::AlignCenter);

        gridLayout_4->addWidget(alert_max_price_title, 3, 0, 1, 1);

        alert_price_high = new QLineEdit(quote_group);
        alert_price_high->setObjectName(QStringLiteral("alert_price_high"));
        sizePolicy.setHeightForWidth(alert_price_high->sizePolicy().hasHeightForWidth());
        alert_price_high->setSizePolicy(sizePolicy);

        gridLayout_4->addWidget(alert_price_high, 3, 1, 1, 1);

        add_alert_btn = new QPushButton(quote_group);
        add_alert_btn->setObjectName(QStringLiteral("add_alert_btn"));
        sizePolicy1.setHeightForWidth(add_alert_btn->sizePolicy().hasHeightForWidth());
        add_alert_btn->setSizePolicy(sizePolicy1);

        gridLayout_4->addWidget(add_alert_btn, 4, 0, 1, 2);


        horizontalLayout->addLayout(gridLayout_4);


        gridLayout_5->addLayout(horizontalLayout, 1, 0, 1, 1);


        gridLayout_13->addWidget(quote_group, 0, 0, 1, 1);

        orders_group = new QFrame(centralwidget);
        orders_group->setObjectName(QStringLiteral("orders_group"));
        sizePolicy.setHeightForWidth(orders_group->sizePolicy().hasHeightForWidth());
        orders_group->setSizePolicy(sizePolicy);
        orders_group->setFrameShape(QFrame::Box);
        gridLayout_8 = new QGridLayout(orders_group);
        gridLayout_8->setObjectName(QStringLiteral("gridLayout_8"));
        gridLayout_6 = new QGridLayout();
        gridLayout_6->setObjectName(QStringLiteral("gridLayout_6"));
        order_title = new QLabel(orders_group);
        order_title->setObjectName(QStringLiteral("order_title"));
        sizePolicy.setHeightForWidth(order_title->sizePolicy().hasHeightForWidth());
        order_title->setSizePolicy(sizePolicy);
        order_title->setAlignment(Qt::AlignCenter);

        gridLayout_6->addWidget(order_title, 0, 0, 1, 1);

        order_table = new QTableWidget(orders_group);
        if (order_table->columnCount() < 5)
            order_table->setColumnCount(5);
        QTableWidgetItem *__qtablewidgetitem3 = new QTableWidgetItem();
        __qtablewidgetitem3->setTextAlignment(Qt::AlignCenter);
        order_table->setHorizontalHeaderItem(0, __qtablewidgetitem3);
        QTableWidgetItem *__qtablewidgetitem4 = new QTableWidgetItem();
        __qtablewidgetitem4->setTextAlignment(Qt::AlignCenter);
        order_table->setHorizontalHeaderItem(1, __qtablewidgetitem4);
        QTableWidgetItem *__qtablewidgetitem5 = new QTableWidgetItem();
        __qtablewidgetitem5->setTextAlignment(Qt::AlignCenter);
        order_table->setHorizontalHeaderItem(2, __qtablewidgetitem5);
        QTableWidgetItem *__qtablewidgetitem6 = new QTableWidgetItem();
        __qtablewidgetitem6->setTextAlignment(Qt::AlignCenter);
        order_table->setHorizontalHeaderItem(3, __qtablewidgetitem6);
        QTableWidgetItem *__qtablewidgetitem7 = new QTableWidgetItem();
        __qtablewidgetitem7->setTextAlignment(Qt::AlignCenter);
        order_table->setHorizontalHeaderItem(4, __qtablewidgetitem7);
        order_table->setObjectName(QStringLiteral("order_table"));
        order_table->horizontalHeader()->setCascadingSectionResizes(true);
        order_table->horizontalHeader()->setDefaultSectionSize(127);
        order_table->horizontalHeader()->setProperty("showSortIndicator", QVariant(true));
        order_table->horizontalHeader()->setStretchLastSection(true);
        order_table->verticalHeader()->setCascadingSectionResizes(true);
        order_table->verticalHeader()->setProperty("showSortIndicator", QVariant(true));
        order_table->verticalHeader()->setStretchLastSection(true);

        gridLayout_6->addWidget(order_table, 1, 0, 1, 1);


        gridLayout_8->addLayout(gridLayout_6, 0, 0, 1, 1);

        gridLayout_7 = new QGridLayout();
        gridLayout_7->setObjectName(QStringLiteral("gridLayout_7"));
        create_order_title = new QLabel(orders_group);
        create_order_title->setObjectName(QStringLiteral("create_order_title"));
        sizePolicy.setHeightForWidth(create_order_title->sizePolicy().hasHeightForWidth());
        create_order_title->setSizePolicy(sizePolicy);
        create_order_title->setAlignment(Qt::AlignCenter);

        gridLayout_7->addWidget(create_order_title, 0, 0, 1, 5);

        order_name_title = new QLabel(orders_group);
        order_name_title->setObjectName(QStringLiteral("order_name_title"));
        sizePolicy.setHeightForWidth(order_name_title->sizePolicy().hasHeightForWidth());
        order_name_title->setSizePolicy(sizePolicy);
        order_name_title->setAlignment(Qt::AlignCenter);

        gridLayout_7->addWidget(order_name_title, 1, 0, 1, 1);

        order_name = new QLineEdit(orders_group);
        order_name->setObjectName(QStringLiteral("order_name"));
        sizePolicy.setHeightForWidth(order_name->sizePolicy().hasHeightForWidth());
        order_name->setSizePolicy(sizePolicy);

        gridLayout_7->addWidget(order_name, 1, 1, 1, 2);

        order_amount_title = new QLabel(orders_group);
        order_amount_title->setObjectName(QStringLiteral("order_amount_title"));
        sizePolicy.setHeightForWidth(order_amount_title->sizePolicy().hasHeightForWidth());
        order_amount_title->setSizePolicy(sizePolicy);
        order_amount_title->setAlignment(Qt::AlignCenter);

        gridLayout_7->addWidget(order_amount_title, 1, 3, 1, 1);

        order_amount = new QLineEdit(orders_group);
        order_amount->setObjectName(QStringLiteral("order_amount"));
        sizePolicy.setHeightForWidth(order_amount->sizePolicy().hasHeightForWidth());
        order_amount->setSizePolicy(sizePolicy);

        gridLayout_7->addWidget(order_amount, 1, 4, 1, 1);

        order_price_title = new QLabel(orders_group);
        order_price_title->setObjectName(QStringLiteral("order_price_title"));
        sizePolicy.setHeightForWidth(order_price_title->sizePolicy().hasHeightForWidth());
        order_price_title->setSizePolicy(sizePolicy);
        order_price_title->setAlignment(Qt::AlignCenter);

        gridLayout_7->addWidget(order_price_title, 2, 0, 1, 1);

        order_price = new QLineEdit(orders_group);
        order_price->setObjectName(QStringLiteral("order_price"));
        sizePolicy.setHeightForWidth(order_price->sizePolicy().hasHeightForWidth());
        order_price->setSizePolicy(sizePolicy);

        gridLayout_7->addWidget(order_price, 2, 1, 1, 2);

        order_expiration_title = new QLabel(orders_group);
        order_expiration_title->setObjectName(QStringLiteral("order_expiration_title"));
        sizePolicy.setHeightForWidth(order_expiration_title->sizePolicy().hasHeightForWidth());
        order_expiration_title->setSizePolicy(sizePolicy);
        order_expiration_title->setAlignment(Qt::AlignCenter);

        gridLayout_7->addWidget(order_expiration_title, 2, 3, 1, 1);

        order_expiration = new QLineEdit(orders_group);
        order_expiration->setObjectName(QStringLiteral("order_expiration"));
        sizePolicy.setHeightForWidth(order_expiration->sizePolicy().hasHeightForWidth());
        order_expiration->setSizePolicy(sizePolicy);

        gridLayout_7->addWidget(order_expiration, 2, 4, 1, 1);

        buy_order = new QRadioButton(orders_group);
        buy_order->setObjectName(QStringLiteral("buy_order"));
        sizePolicy1.setHeightForWidth(buy_order->sizePolicy().hasHeightForWidth());
        buy_order->setSizePolicy(sizePolicy1);

        gridLayout_7->addWidget(buy_order, 3, 1, 1, 1);

        sell_order = new QRadioButton(orders_group);
        sell_order->setObjectName(QStringLiteral("sell_order"));
        sizePolicy1.setHeightForWidth(sell_order->sizePolicy().hasHeightForWidth());
        sell_order->setSizePolicy(sizePolicy1);

        gridLayout_7->addWidget(sell_order, 3, 4, 1, 1);

        create_order_btn = new QPushButton(orders_group);
        create_order_btn->setObjectName(QStringLiteral("create_order_btn"));
        sizePolicy1.setHeightForWidth(create_order_btn->sizePolicy().hasHeightForWidth());
        create_order_btn->setSizePolicy(sizePolicy1);

        gridLayout_7->addWidget(create_order_btn, 4, 2, 1, 2);


        gridLayout_8->addLayout(gridLayout_7, 1, 0, 1, 1);


        gridLayout_13->addWidget(orders_group, 0, 1, 1, 1);

        owned_stock_group = new QFrame(centralwidget);
        owned_stock_group->setObjectName(QStringLiteral("owned_stock_group"));
        sizePolicy.setHeightForWidth(owned_stock_group->sizePolicy().hasHeightForWidth());
        owned_stock_group->setSizePolicy(sizePolicy);
        owned_stock_group->setFrameShape(QFrame::Box);
        gridLayout_10 = new QGridLayout(owned_stock_group);
        gridLayout_10->setObjectName(QStringLiteral("gridLayout_10"));
        gridLayout_9 = new QGridLayout();
        gridLayout_9->setObjectName(QStringLiteral("gridLayout_9"));
        owned_stock_title = new QLabel(owned_stock_group);
        owned_stock_title->setObjectName(QStringLiteral("owned_stock_title"));
        sizePolicy2.setHeightForWidth(owned_stock_title->sizePolicy().hasHeightForWidth());
        owned_stock_title->setSizePolicy(sizePolicy2);
        owned_stock_title->setAlignment(Qt::AlignCenter);

        gridLayout_9->addWidget(owned_stock_title, 0, 0, 1, 1);

        owned_stock_table = new QTableWidget(owned_stock_group);
        if (owned_stock_table->columnCount() < 3)
            owned_stock_table->setColumnCount(3);
        QTableWidgetItem *__qtablewidgetitem8 = new QTableWidgetItem();
        __qtablewidgetitem8->setTextAlignment(Qt::AlignCenter);
        owned_stock_table->setHorizontalHeaderItem(0, __qtablewidgetitem8);
        QTableWidgetItem *__qtablewidgetitem9 = new QTableWidgetItem();
        __qtablewidgetitem9->setTextAlignment(Qt::AlignCenter);
        owned_stock_table->setHorizontalHeaderItem(1, __qtablewidgetitem9);
        QTableWidgetItem *__qtablewidgetitem10 = new QTableWidgetItem();
        __qtablewidgetitem10->setTextAlignment(Qt::AlignCenter);
        owned_stock_table->setHorizontalHeaderItem(2, __qtablewidgetitem10);
        owned_stock_table->setObjectName(QStringLiteral("owned_stock_table"));
        owned_stock_table->horizontalHeader()->setCascadingSectionResizes(true);
        owned_stock_table->horizontalHeader()->setDefaultSectionSize(212);
        owned_stock_table->horizontalHeader()->setProperty("showSortIndicator", QVariant(true));
        owned_stock_table->horizontalHeader()->setStretchLastSection(true);
        owned_stock_table->verticalHeader()->setCascadingSectionResizes(true);
        owned_stock_table->verticalHeader()->setProperty("showSortIndicator", QVariant(true));
        owned_stock_table->verticalHeader()->setStretchLastSection(true);

        gridLayout_9->addWidget(owned_stock_table, 1, 0, 1, 1);


        gridLayout_10->addLayout(gridLayout_9, 0, 0, 1, 1);


        gridLayout_13->addWidget(owned_stock_group, 1, 0, 1, 1);

        messages_group = new QFrame(centralwidget);
        messages_group->setObjectName(QStringLiteral("messages_group"));
        sizePolicy.setHeightForWidth(messages_group->sizePolicy().hasHeightForWidth());
        messages_group->setSizePolicy(sizePolicy);
        messages_group->setFrameShape(QFrame::Box);
        gridLayout_12 = new QGridLayout(messages_group);
        gridLayout_12->setObjectName(QStringLiteral("gridLayout_12"));
        gridLayout_11 = new QGridLayout();
        gridLayout_11->setObjectName(QStringLiteral("gridLayout_11"));
        messages_title = new QLabel(messages_group);
        messages_title->setObjectName(QStringLiteral("messages_title"));
        sizePolicy2.setHeightForWidth(messages_title->sizePolicy().hasHeightForWidth());
        messages_title->setSizePolicy(sizePolicy2);
        messages_title->setAlignment(Qt::AlignCenter);

        gridLayout_11->addWidget(messages_title, 0, 0, 1, 1);

        messages = new QPlainTextEdit(messages_group);
        messages->setObjectName(QStringLiteral("messages"));
        messages->setReadOnly(true);

        gridLayout_11->addWidget(messages, 1, 0, 1, 1);


        gridLayout_12->addLayout(gridLayout_11, 0, 0, 1, 1);


        gridLayout_13->addWidget(messages_group, 1, 1, 1, 1);

        MainWindow->setCentralWidget(centralwidget);

        retranslateUi(MainWindow);

        QMetaObject::connectSlotsByName(MainWindow);
    } // setupUi

    void retranslateUi(QMainWindow *MainWindow)
    {
        MainWindow->setWindowTitle(QApplication::translate("MainWindow", "Client Homebroker", Q_NULLPTR));
        quote_title->setText(QApplication::translate("MainWindow", "Cota\303\247\303\265es", Q_NULLPTR));
        update_btn->setText(QApplication::translate("MainWindow", "Atualizar", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem = quote_table->horizontalHeaderItem(0);
        ___qtablewidgetitem->setText(QApplication::translate("MainWindow", "Nome", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem1 = quote_table->horizontalHeaderItem(1);
        ___qtablewidgetitem1->setText(QApplication::translate("MainWindow", "Cota\303\247\303\243o", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem2 = quote_table->horizontalHeaderItem(2);
        ___qtablewidgetitem2->setText(QApplication::translate("MainWindow", "Alerta Registradro", Q_NULLPTR));
        quote_action_title->setText(QApplication::translate("MainWindow", "Adicionar ou remover cota\303\247\303\243o", Q_NULLPTR));
        quote_add_title->setText(QApplication::translate("MainWindow", "Nome da a\303\247\303\243o", Q_NULLPTR));
        add_quote_btn->setText(QApplication::translate("MainWindow", "Adicionar", Q_NULLPTR));
        remove_quote_btn->setText(QApplication::translate("MainWindow", "Remover", Q_NULLPTR));
        quote_alert_title->setText(QApplication::translate("MainWindow", "Adicionar ou remover alerta", Q_NULLPTR));
        alert_name_title->setText(QApplication::translate("MainWindow", "Nome da a\303\247\303\243o", Q_NULLPTR));
        alert_price_low_title->setText(QApplication::translate("MainWindow", "Pre\303\247o m\303\255nimo", Q_NULLPTR));
        alert_max_price_title->setText(QApplication::translate("MainWindow", "Pre\303\247o M\303\241ximo", Q_NULLPTR));
        add_alert_btn->setText(QApplication::translate("MainWindow", "Adicionar", Q_NULLPTR));
        order_title->setText(QApplication::translate("MainWindow", "Ordens de compra e venda ativas", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem3 = order_table->horizontalHeaderItem(0);
        ___qtablewidgetitem3->setText(QApplication::translate("MainWindow", "Nome", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem4 = order_table->horizontalHeaderItem(1);
        ___qtablewidgetitem4->setText(QApplication::translate("MainWindow", "Pre\303\247o", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem5 = order_table->horizontalHeaderItem(2);
        ___qtablewidgetitem5->setText(QApplication::translate("MainWindow", "Quantidade", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem6 = order_table->horizontalHeaderItem(3);
        ___qtablewidgetitem6->setText(QApplication::translate("MainWindow", "Tipo", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem7 = order_table->horizontalHeaderItem(4);
        ___qtablewidgetitem7->setText(QApplication::translate("MainWindow", "Expira\303\247\303\243o", Q_NULLPTR));
        create_order_title->setText(QApplication::translate("MainWindow", "Criar Ordem", Q_NULLPTR));
        order_name_title->setText(QApplication::translate("MainWindow", "Nome da a\303\247\303\243o", Q_NULLPTR));
        order_amount_title->setText(QApplication::translate("MainWindow", "Quantidade", Q_NULLPTR));
        order_price_title->setText(QApplication::translate("MainWindow", "Pre\303\247o", Q_NULLPTR));
        order_expiration_title->setText(QApplication::translate("MainWindow", "Expira\303\247\303\243o (minutos)", Q_NULLPTR));
        buy_order->setText(QApplication::translate("MainWindow", "Comprar", Q_NULLPTR));
        sell_order->setText(QApplication::translate("MainWindow", "Vender", Q_NULLPTR));
        create_order_btn->setText(QApplication::translate("MainWindow", "Criar", Q_NULLPTR));
        owned_stock_title->setText(QApplication::translate("MainWindow", "Carteira", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem8 = owned_stock_table->horizontalHeaderItem(0);
        ___qtablewidgetitem8->setText(QApplication::translate("MainWindow", "Nome", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem9 = owned_stock_table->horizontalHeaderItem(1);
        ___qtablewidgetitem9->setText(QApplication::translate("MainWindow", "Quantidade", Q_NULLPTR));
        QTableWidgetItem *___qtablewidgetitem10 = owned_stock_table->horizontalHeaderItem(2);
        ___qtablewidgetitem10->setText(QApplication::translate("MainWindow", " Valor Total", Q_NULLPTR));
        messages_title->setText(QApplication::translate("MainWindow", "Mensagens", Q_NULLPTR));
    } // retranslateUi

};

namespace Ui {
    class MainWindow: public Ui_MainWindow {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_MAIN_WINDOW_H
