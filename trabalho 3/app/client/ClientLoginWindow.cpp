#include "ClientLoginWindow.h"
#include "gui_client.h"
#include "Client.h"
#include <iostream>
#include <string>
#include <ctime>

ClientLoginWindow::ClientLoginWindow(Client &client_) : QMainWindow(), _ui(Ui::LoginWindow()), _client(client_)
{
    _is_warning_active = false;
    this->_ui.setupUi(this);
    this->_ui.invalid_name_msg->setVisible(false);
    
    connect(this->_ui.login_btn, SIGNAL(released()), this, SLOT(_onLoginBtn()));
}

void ClientLoginWindow::_onLoginBtn()
{
    std::string client_name = this->_ui.client_name->text().toUtf8().constData();
    std::cout << "Digitou o nome " << client_name << std::endl;
    if (!this->_is_warning_active)
    {
        this->_ui.invalid_name_msg->setVisible(true);
        this->_ui.client_name->setVisible(false);
        this->_ui.client_name_title->setVisible(false);
        this->_is_warning_active = true;
    }
    else
    {
        this->_ui.client_name->clear());
        this->_ui.invalid_name_msg->setVisible(false);
        this->_ui.client_name->setVisible(true);
        this->_ui.client_name_title->setVisible(true);
        this->_is_warning_active = false;
    }
}

