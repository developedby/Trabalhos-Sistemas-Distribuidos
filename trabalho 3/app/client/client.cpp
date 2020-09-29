// #include <cpprest/http_client.h>
// #include <cpprest/json.h>
// #pragma comment(lib, "cpprest_2_10")
 
// using namespace web;
// using namespace web::http;
// using namespace web::http::client;
 
// #include <iostream>
// using namespace std;
 
// void display_json(
//    json::value const & jvalue, 
//    utility::string_t const & prefix)
// {
//    std::cout << prefix << jvalue.serialize() << endl;
// }
 
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

// #include "gui.h"

#include "MainWindow.h"

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    MainWindow teste;

    // QMainWindow widget;
    // Ui::MainWindow ui;
    // ui.setupUi(&widget);
    
    // // ui.quote_table->setColumnWidth(0, 213);
    // // ui.quote_table->setColumnWidth(1, 400);
    // // ui.quote_table->setColumnWidth(2, 21);

    // widget.show();
    return app.exec();
}