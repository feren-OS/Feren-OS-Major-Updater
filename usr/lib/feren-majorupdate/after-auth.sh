#!/bin/bash

/usr/bin/feren-majorupdate-commands "${@//[^a-zA-Z0-9_]/}"
exit $?
