#!/bin/sh

python3 -m Pyro5.nameserver &
python3 ./server/server.py &
python3 ./client/client.py &
