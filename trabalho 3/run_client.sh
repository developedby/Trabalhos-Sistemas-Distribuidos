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
./client