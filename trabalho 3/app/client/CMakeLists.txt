cmake_minimum_required(VERSION 3.9)
project(client)

find_package(Boost REQUIRED COMPONENTS system)
find_package(OpenSSL REQUIRED)
find_package(cpprestsdk REQUIRED)

find_package(Qt5 COMPONENTS Core Widgets REQUIRED)
include_directories(${Qt5Widgets_INCLUDE_DIRS})
include_directories(${Qt5Core_INCLUDE_DIRS})

set(CMAKE_AUTOMOC ON)



add_executable(client MainWindow.cpp client.cpp)
target_link_libraries(client PRIVATE cpprestsdk::cpprest  ${Boost_LIBRARIES}
    ${OPENSSL_LIBRARIES}
    Qt5::Widgets)