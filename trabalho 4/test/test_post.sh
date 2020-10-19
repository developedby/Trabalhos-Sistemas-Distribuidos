#!/bin/bash
curl -X POST -H "Content-Type: application/json" -d '{"client_name": "alefe20", "ticker": "a"}' 127.0.0.1:5000/quote
curl -X POST -H "Content-Type: application/json" -d '{"ticker": "a", "lower_limit": 1000, "upper_limit": 2000, "client_name": "alefe20"}' 127.0.0.1:5000/limit
