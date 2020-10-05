#ifndef SSE_H
#define SSE_H

#include <string>
#include <functional>

#define MAX_HANDLES 10

// void hold_sse(std::string url, size_t *callback_func(char *ptr, size_t size, size_t nmemb, void *userdata));
void hold_sse(std::string url, std::function<void(std::string result)> callback_func);

#endif