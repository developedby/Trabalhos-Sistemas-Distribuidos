#!/bin/bash
cd ./app/homebroker
export FLASK_APP=./homebroker.py
echo "Digite a porta onde o homebroker deve rodar: "
read port
flask run -p $port 