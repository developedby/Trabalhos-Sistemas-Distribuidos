#include "Client.h"
#include <QtWidgets/QApplication>

#include <cpprest/ws_client.h>

//Função main, irá criar um cliente, passando a uri do servidor
int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    int port = 4000;
    if (argc >= 2)
    {
        port = std::stoi(argv[1]);
    }

    std::string uri = "http://localhost:" + std::to_string(port) + "/";
    Client client(uri);
    
    return app.exec();
}