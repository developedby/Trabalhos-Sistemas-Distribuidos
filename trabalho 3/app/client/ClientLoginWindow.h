#ifndef CLIENT_LOGIN_WINDOW
#define CLIENT_LOGIN_WINDOW

#include "gui_client.h"
#include "Client.h"

class ClientLoginWindow : public QMainWindow
{
    Q_OBJECT
    Ui::LoginWindow _ui;
    Client &_client;
    bool _is_warning_active;

private slots:
    void _onLoginBtn();

public:
    ClientLoginWindow(Client &client_);

    // void show();
    // void close();
};
#endif