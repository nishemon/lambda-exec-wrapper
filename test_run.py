#!/usr/bin/python

import apigateway
import json
import sys

f = open(sys.argv[1], 'r')
event = json.load(f)
f.close()

print apigateway.lambda_handler(event, None)

