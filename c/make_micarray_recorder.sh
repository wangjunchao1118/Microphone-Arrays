#!/bin/bash

# [ -f ./micarray_recorder ] && rm ./micarray_recorder

g++ -c -std=c++11 -Wall -Wextra -std=gnu++11 -I ../cpp/driver ./micarray_recorder.cpp  -o ./micarray_recorder.cpp.o
g++ ./micarray_recorder.cpp.o  -o micarray_recorder  -rdynamic  ../build/demos/driver/libmatrix_creator_hal.a -lpthread -lwiringPi -lwiringPiDev -lcrypt -lfftw3f
