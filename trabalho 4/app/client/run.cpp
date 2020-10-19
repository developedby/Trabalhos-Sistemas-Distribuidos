#include "Client.h"
#include <QtWidgets/QApplication>

#include <cpprest/ws_client.h>

//Função main, irá criar um cliente, passando a uri do servidor
int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    Client client("http://localhost:5000/");
    
    return app.exec();
}