#ifndef CLIENT_LOGIN_WINDOW
#define CLIENT_LOGIN_WINDOW

#include "gui_client.h"
#include "Client.h"

class ClientLoginWindow : public QMainWindow
{
    Q_OBJECT
    Ui::LoginWindow _ui; //Janela de login
    Client &_client; //Referência para a classe client
    bool _is_warning_active; //Setado caso houve um erro

    /** Apaga a mensagem de erro da janela
     */
    void _clearError();

private slots:
    /** Dependendo do status interno (_is_warning_active), vai chamar a Client::login ou _clearError
     */
    void _onLoginBtn();

public:
    /** Cria ClientLoginWindow - uma classe usada para interfacear a janela de login
     *  Vai mapear o botão de Ok para _onLoginBtn
     *
     *  @param client_              Referência para a classe Client
     */
    ClientLoginWindow(Client &client_);
public slots:
    /** Mostra a mensagem de erro na janela de login
     */
    void showError();
};
#endif