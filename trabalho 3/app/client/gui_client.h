/********************************************************************************
** Form generated from reading UI file 'login.ui'
**
** Created by: Qt User Interface Compiler version 5.9.5
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef LOGIN_H
#define LOGIN_H

#include <QtCore/QVariant>
#include <QtWidgets/QAction>
#include <QtWidgets/QApplication>
#include <QtWidgets/QButtonGroup>
#include <QtWidgets/QGridLayout>
#include <QtWidgets/QHeaderView>
#include <QtWidgets/QLabel>
#include <QtWidgets/QLineEdit>
#include <QtWidgets/QMainWindow>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_LoginWindow
{
public:
    QWidget *centralwidget;
    QGridLayout *gridLayout;
    QLabel *client_name_title;
    QPushButton *login_btn;
    QLineEdit *client_name;
    QLabel *invalid_name_msg;

    void setupUi(QMainWindow *LoginWindow)
    {
        if (LoginWindow->objectName().isEmpty())
            LoginWindow->setObjectName(QStringLiteral("LoginWindow"));
        LoginWindow->resize(224, 166);
        centralwidget = new QWidget(LoginWindow);
        centralwidget->setObjectName(QStringLiteral("centralwidget"));
        gridLayout = new QGridLayout(centralwidget);
        gridLayout->setObjectName(QStringLiteral("gridLayout"));
        client_name_title = new QLabel(centralwidget);
        client_name_title->setObjectName(QStringLiteral("client_name_title"));
        QSizePolicy sizePolicy(QSizePolicy::Preferred, QSizePolicy::Fixed);
        sizePolicy.setHorizontalStretch(0);
        sizePolicy.setVerticalStretch(0);
        sizePolicy.setHeightForWidth(client_name_title->sizePolicy().hasHeightForWidth());
        client_name_title->setSizePolicy(sizePolicy);
        client_name_title->setAlignment(Qt::AlignCenter);

        gridLayout->addWidget(client_name_title, 0, 0, 1, 1);

        login_btn = new QPushButton(centralwidget);
        login_btn->setObjectName(QStringLiteral("login_btn"));
        login_btn->setEnabled(true);

        gridLayout->addWidget(login_btn, 3, 0, 1, 1);

        client_name = new QLineEdit(centralwidget);
        client_name->setObjectName(QStringLiteral("client_name"));
        QSizePolicy sizePolicy1(QSizePolicy::Expanding, QSizePolicy::Fixed);
        sizePolicy1.setHorizontalStretch(0);
        sizePolicy1.setVerticalStretch(0);
        sizePolicy1.setHeightForWidth(client_name->sizePolicy().hasHeightForWidth());
        client_name->setSizePolicy(sizePolicy1);

        gridLayout->addWidget(client_name, 2, 0, 1, 1);

        invalid_name_msg = new QLabel(centralwidget);
        invalid_name_msg->setObjectName(QStringLiteral("invalid_name_msg"));
        invalid_name_msg->setEnabled(true);
        sizePolicy.setHeightForWidth(invalid_name_msg->sizePolicy().hasHeightForWidth());
        invalid_name_msg->setSizePolicy(sizePolicy);
        invalid_name_msg->setStyleSheet(QStringLiteral("color: rgb(255, 0, 0);"));
        invalid_name_msg->setScaledContents(false);
        invalid_name_msg->setAlignment(Qt::AlignCenter);

        gridLayout->addWidget(invalid_name_msg, 1, 0, 1, 1);

        LoginWindow->setCentralWidget(centralwidget);

        retranslateUi(LoginWindow);

        QMetaObject::connectSlotsByName(LoginWindow);
    } // setupUi

    void retranslateUi(QMainWindow *LoginWindow)
    {
        LoginWindow->setWindowTitle(QApplication::translate("LoginWindow", "Login", Q_NULLPTR));
        client_name_title->setText(QApplication::translate("LoginWindow", "Insira o nome de usu\303\241rio", Q_NULLPTR));
        login_btn->setText(QApplication::translate("LoginWindow", "OK", Q_NULLPTR));
        invalid_name_msg->setText(QApplication::translate("LoginWindow", "Nome n\303\243o permitido", Q_NULLPTR));
    } // retranslateUi

};

namespace Ui {
    class LoginWindow: public Ui_LoginWindow {};
} // namespace Ui

QT_END_NAMESPACE

#endif // LOGIN_H
