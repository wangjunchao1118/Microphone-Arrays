/*
 * Copyright 2016 <Admobilize>
 * All rights reserved.
 */

#include <wiringPi.h>
#include <stdio.h>
#include <string>
#include <fstream>
#include <iostream>
#include <valarray>

#include <sys/types.h>
#include <sys/stat.h>
#include <time.h>

#include <unistd.h>
#include <utility>
#include <memory>
#include <pthread.h>
#include <sstream>
#include <mqueue.h>
#include <fcntl.h>

#include "../cpp/driver/everloop_image.h"
#include "../cpp/driver/everloop.h"
#include "../cpp/driver/imu_data.h"
#include "../cpp/driver/imu_sensor.h"

#include "../cpp/driver/gpio_control.h"
#include "../cpp/driver/microphone_array.h"
#include "../cpp/driver/wishbone_bus.h"

#define BUFFER_SAMPLES_PER_CHANNEL	16000 //1 second of recording
#define STREAMING_CHANNELS			9 // 8 single channels + 1 beamforming channel

const int32_t bufferByteSize = STREAMING_CHANNELS * BUFFER_SAMPLES_PER_CHANNEL * sizeof(int16_t);

bool recording = false;
bool leding = false;
bool buttoncommand = false;
bool oldcommand = false;

//double buffer of SAMPLES_PER_CHANNEL*9 samples each
int16_t buffer[2][STREAMING_CHANNELS][BUFFER_SAMPLES_PER_CHANNEL];

pthread_mutex_t bufferMutex[2];

namespace hal = matrix_hal;

void *recorder(void*);
void *record2Disk(void*);
void *led(void*);
void *button(void*);
void Recorder(void);
hal::WishboneBus bus;
hal::MicrophoneArray mics;
hal::GPIOControl gpio;
hal::Everloop everloop;
hal::EverloopImage image1d;

int main() {
	
	bus.SpiInit();
	mics.Setup(&bus);
	gpio.Setup(&bus);  // for button
	everloop.Setup(&bus);
	
	pthread_t buttonThread;
	pthread_t recorderThread;
	pthread_t ledThread;
	pthread_mutexattr_t mutexAttr;
	pthread_mutexattr_init(&mutexAttr);
	pthread_mutexattr_settype(&mutexAttr, PTHREAD_MUTEX_RECURSIVE);
	for (int i = 0; i < 2; i++) {
	  pthread_mutex_init(&bufferMutex[i], &mutexAttr);
	}
	pthread_create(&buttonThread, NULL, button, NULL);
		
	while (true) { 	
		
		if ( (oldcommand == false) && (buttoncommand == true) ) {
			recording = true;
			leding = true;
			std::cout<< "start recording" << std::endl;
			pthread_create(&recorderThread, NULL, recorder, NULL);
			pthread_create(&ledThread, NULL, led, NULL);
		}
		else if ( (oldcommand == true) && (buttoncommand == true) ){
			std::cout<< "recording" << std::endl;
		}
		else if ( (oldcommand == false) && (buttoncommand == false) ){
			std::cout<< " no recording" << std::endl;	
		}
		else { //( (oldcommand == true) && (buttoncommand == false) )
			std::cout<< "stop recording" << std::endl;
			recording = false;
			leding = false;	
			pthread_join(recorderThread, NULL);
			pthread_join(ledThread, NULL);
		}
		oldcommand = buttoncommand;
		sleep(1);
	}
	pthread_join(buttonThread, NULL);				
	return 0;
}

void *button(void*) {

	unsigned char pin = 0;
	gpio.SetMode(pin, 0); // 0 is input mode

	uint16_t read_data = 0;

	while (true) {
		read_data = gpio.GetGPIOValue(0);
		if (read_data == 1){ 
			buttoncommand = true;
		}
		else {
			buttoncommand = false;	
		}
		usleep(10000);
	}	
	pthread_exit(NULL);
}

void *led(void*) {
	
	unsigned counter = 0;

	while (leding) {
		for (hal::LedValue& led : image1d.leds) {
			led.red = 0;
			led.green = 0;
			led.blue = 0;
			led.white = 0;
		}
		image1d.leds[(counter / 34) % 35].green = 30;
		everloop.Write(&image1d);
		++counter;
		usleep(20000);
	}
	for (auto& led : image1d.leds) {
		led.red = 0;
		led.green = 0;
		led.blue = 0;
		led.white = 0;
    }
    everloop.Write(&image1d);
	pthread_exit(NULL);
}
void *recorder(void*) {	
	
	int32_t buffer_switch = 0;

	pthread_mutex_lock(&bufferMutex[buffer_switch]);
		
	mics.CalculateDelays(0, 0, 1000, 320 * 1000);
	
	pthread_t writeThread;
	pthread_create(&writeThread, NULL, record2Disk, NULL);
	mics.SetGain(8);	
	while (recording) {  		
		int32_t step = 0;
		bool bufferFull = false;
		
		while (!bufferFull){
			mics.Read(); /* Reading 8-mics buffer from de FPGA */
			for (int32_t s = 0; s < 128; s++) { // 128 = 1024/8 
				for (int16_t c = 0; c < mics.Channels(); c++) { /* mics.Channels()=8 */
					buffer[buffer_switch][c][step] = mics.At(s, c);
				}
				buffer[buffer_switch][mics.Channels()][step] = mics.Beam(s);
				step++;

    		}
			if (step == BUFFER_SAMPLES_PER_CHANNEL) {
				bufferFull = true; // jump while(!bufferFull)
				std::cerr << "buffer index (" << __FUNCTION__ << "):" << buffer_switch << std::endl;
				pthread_mutex_unlock(&bufferMutex[buffer_switch]);

				pthread_mutex_lock(&bufferMutex[(buffer_switch + 1) % 2]);
				buffer_switch = (buffer_switch + 1) % 2;					
				//break; // jump for(int32_t s = 0; s < 128; s++)
			}	
		}		
	}
	pthread_mutex_unlock(&bufferMutex[buffer_switch]);
	pthread_join(writeThread, NULL);
	pthread_exit(NULL);
}

//#define NCHANNEL   9
void *record2Disk(void*) {
  using namespace std;	
	int32_t buffer_switch = 0;
	std::string filenameArray[STREAMING_CHANNELS];
	std::string filepath;
	const unsigned short samplePrecision = 16;
	FILE* file[STREAMING_CHANNELS];
	
	time_t timeObj;
    time(&timeObj);
    tm *pTime = gmtime(&timeObj);
    char dirpath[1024];
    sprintf(dirpath, "/home/pi/wjc/NTUrecording-data/%d_%d_%d_%d_%d_%d/", pTime->tm_year+1900, pTime->tm_mon +1 , pTime->tm_mday, pTime->tm_hour+8, pTime->tm_min, pTime->tm_sec);
	 mkdir(dirpath, S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
		
	for (uint16_t c = 0; c < STREAMING_CHANNELS; c++){
		filenameArray[c] = "c" + std::to_string(c) + ".raw";
		filepath = std::string(dirpath) + filenameArray[c];
		file[c] = fopen(filepath.c_str(), "wb");
	}
		
	while (recording){
		
	  if(pthread_mutex_trylock(&bufferMutex[buffer_switch]) == 0 ) {
		for (uint16_t c = 0; c < STREAMING_CHANNELS; c++) {
			fwrite((const char*)buffer[buffer_switch][c], samplePrecision/8, BUFFER_SAMPLES_PER_CHANNEL, file[c]);		
		}
		std::cerr << "buffer index (" << __FUNCTION__ << "):" << buffer_switch << std::endl;
		pthread_mutex_unlock(&bufferMutex[buffer_switch]);
		buffer_switch = (buffer_switch + 1) % 2;
	  }
	}
        // todo: to write residul buffer
	for(uint16_t c =0; c < STREAMING_CHANNELS; c++) {
	  fwrite((const char*)buffer[buffer_switch][c], samplePrecision/8, BUFFER_SAMPLES_PER_CHANNEL, file[c]);		
	}
	std::cerr << "buffer index (" << __FUNCTION__ << "):" << buffer_switch << std::endl;
	for (uint16_t c = 0; c < STREAMING_CHANNELS; c++){
		fclose(file[c]);
	}
	pthread_exit(NULL);	
}
