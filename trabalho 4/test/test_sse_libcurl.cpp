#include <curl/curl.h>
#include <iostream>
#include <string>

#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
#include <stdio.h>

const int MAX_HANDLES = 10;

static size_t on_data(char *ptr, size_t size, size_t nmemb, void *userdata)
{
  std::cout << std::string(ptr, size * nmemb);
  
  return size * nmemb;
}

static const char* on_verify(CURL* curl) {
  #define EXPECTED_CONTENT_TYPE "text/event-stream"
  
  static const char expected_content_type[] = EXPECTED_CONTENT_TYPE;

  char* content_type;
  curl_easy_getinfo(curl, CURLINFO_CONTENT_TYPE, &content_type); 
  if(!content_type)
    content_type = "";

  if(!strncmp(content_type, expected_content_type, strlen(expected_content_type)))
    return 0;
  
  return "Invalid content_type, should be '" EXPECTED_CONTENT_TYPE "'.";
}

static CURL* curl_handle(int index) {
    static int curl_initialised = 0;
    static CURL *curl_handles[MAX_HANDLES];

    if(!curl_initialised) {
        curl_initialised = 1;
        memset(curl_handles, 0, sizeof(curl_handles));
        curl_global_init(CURL_GLOBAL_ALL);  /* In windows, this will init the winsock stuff */ 
        atexit(curl_global_cleanup);
    }

    CURL* curl = curl_handles[index];
    if(!curl) {
        curl = curl_handles[index] = curl_easy_init();
        if(!curl)
            exit(0);
    }

    curl_easy_setopt(curl, CURLOPT_NOPROGRESS, 1);

    return curl;
}

int main()
{
    const char* http_headers = "Accept: text/event-stream";
    const char* url = "localhost:5000/login?client_name=as";
    CURL *curl = curl_handle(0);

    curl_easy_setopt(curl, CURLOPT_URL, url);

    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, http_headers);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers); 

    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, on_data);

    CURLcode res = curl_easy_perform(curl);
    long response_code; 
    const char* effective_url = 0;

    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code); 
    if(response_code < 200 || response_code >= 300) {
        if(!effective_url)
            curl_easy_getinfo(curl, CURLINFO_EFFECTIVE_URL, &effective_url); 

        fprintf(stderr, "%s: HTTP(S) status code %ld\n", effective_url, response_code);
        exit(1);
    }

    const char* verification_error = on_verify ? on_verify(curl) : 0;
    if(verification_error) {
        if(!effective_url)
            curl_easy_getinfo(curl, CURLINFO_EFFECTIVE_URL, &effective_url); 

        fprintf(stderr, "%s: %s\n", effective_url, verification_error);
        exit(1);
    }

    if(headers)
        curl_slist_free_all(headers);
}