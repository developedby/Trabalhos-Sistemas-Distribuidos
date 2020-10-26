#!/bin/bash
cd ./app/client
if [ ! -d "./build" ]
then
    mkdir build
    cd build
    cmake ..
else
    cd build
fi

make

echo "Digite a porta onde o homebroker está rodando: "
read port
./client $port