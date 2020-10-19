#ifndef SSE_H
#define SSE_H

#include <string>
#include <functional>

#define MAX_HANDLES 10

/** Cria uma conexão http permanete com o servidor, usando sse.
 * 
 *  @param url                  URL HTTP para fazer o login
 *  @param callback_func        Função que será chamada quando tiver um evento sse
 */
void hold_sse(std::string url, std::function<void(std::string result)> callback_func);

#endif