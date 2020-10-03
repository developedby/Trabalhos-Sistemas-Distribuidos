// #include <cpprest/http_client.h>
// #include <cpprest/json.h>
// #pragma comment(lib, "cpprest_2_10")
 
// using namespace web;
// using namespace web::http;
// using namespace web::http::client;
 
// #include <iostream>
// using namespace std;
 

 
// pplx::task<http_response> make_task_request(
//    http_client & client,
//    method mtd,
//    json::value const & jvalue)
// {
//    return (mtd == methods::GET || mtd == methods::HEAD) ?
//       client.request(mtd, "/") :
//       client.request(mtd, "/", jvalue);
// }
 
// void make_request(
//    http_client & client, 
//    method mtd, 
//    json::value const & jvalue)
// {
//    make_task_request(client, mtd, jvalue)
//       .then([](http_response response)
//       {
//          if (response.status_code() == status_codes::OK)
//          {
//             return response.extract_json();
//          }
//          return pplx::task_from_result(json::value());
//       })
//       .then([](pplx::task<json::value> previousTask)
//       {
//          try
//          {
//             display_json(previousTask.get(), "R: ");
//          }
//          catch (http_exception const & e)
//          {
//             std::cout << e.what() << endl;
//          }
//       })
//       .wait();
// }
 
// int main()
// {
//    http_client client_get(U("http://localhost:4444"));
//    http_client client_put(U("http://localhost:4444/update"));
//    http_client client_delete(U("http://localhost:4444/delete"));
//    http_client client_post(U("http://localhost:4444/create"));
 
//    auto putvalue = json::value::object();
//    putvalue["one"] = json::value::string("100");
//    putvalue["two"] = json::value::string("200");
 
//    std::cout << "\nPUT (add values)\n";
//    display_json(putvalue, "S: ");
//    make_request(client_put, methods::PUT, putvalue);
 
//    auto getvalue = json::value::array();
//    getvalue[0] = json::value::string("one");
//    getvalue[1] = json::value::string("two");
//    getvalue[2] = json::value::string("three");
 
//    std::cout << "\nPOST (get some values)\n";
//    display_json(getvalue, "S: ");
//    make_request(client_post, methods::POST, getvalue);
 
//    auto delvalue = json::value::array();
//    delvalue[0] = json::value::string("one");
 
//    std::cout << "\nDELETE (delete values)\n";
//    display_json(delvalue, "S: ");
//    make_request(client_delete, methods::DEL, delvalue);
 
//    std::cout << "\nPOST (get some values)\n";
//    display_json(getvalue, "S: ");
//    make_request(client_post, methods::POST, getvalue);
 
//    auto nullvalue = json::value::null();
 
//    std::cout << "\nGET (get all values)\n";
//    display_json(nullvalue, "S: ");
//    make_request(client_get, methods::GET, nullvalue);
 
//    return 0;
// }


#include "Client.h"
#include <QtWidgets/QApplication>

#include <cpprest/ws_client.h>
using namespace web;
using namespace web::websockets::client;

void teste_websockets()
{
    websocket_client client;
    bool conected = false;
    client.connect(U("ws://localhost:8767")).then([&conected](){conected = true; std::cout << "massa" << std::endl;});
    while(!conected)
    {
        usleep(1000000);
    }
    std::cout << "conecout" << std::endl;
    websocket_outgoing_message msg;
    std::cout << "stando msg" << std::endl;
    msg.set_utf8_message("Alefe");
    std::cout << "mandando msg" << std::endl;
    conected = false;
    client.send(msg).then([&conected](){conected = true; std::cout << "massa2" << std::endl;});
    while(!conected)
    {
        usleep(1000000);
    }
    std::cout << "recebi resposta" << std::endl;
    while(true)
    {
        client.receive().then([](websocket_incoming_message msg) 
        {
            std::cout << "recebi resposta" << std::endl;
            return msg.extract_string();
        }).then([](std::string body) 
        {
            std::cout << "printando resposta" << std::endl;
            std::cout << body << std::endl;
        });
        std::cout << "esperando coisas" << std::endl;
    }
}

int main(int argc, char *argv[])
{
    
    // time_t timestamp = time(NULL);
    // std::cout << "time int: " << timestamp << std::endl;
    // std::string time_string = time_to_string(&timestamp);
    // time_t timestamp2 = string_to_time(time_string);
    // std::cout << "time int depois: " << timestamp2 << std::endl;
    QApplication app(argc, argv);
    Client client("http://localhost:5000/");
    return app.exec();
   //  MainWindow teste;

    // QMainWindow widget;
    // Ui::MainWindow ui;
    // ui.setupUi(&widget);
    
    // // ui.quote_table->setColumnWidth(0, 213);
    // // ui.quote_table->setColumnWidth(1, 400);
    // // ui.quote_table->setColumnWidth(2, 21);

    // widget.show();
    
}