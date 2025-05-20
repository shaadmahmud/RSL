#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "hardware/timer.h"
#include "lib/pico-ads1115/lib/include/ads1115.h"

// Define I2C port
#define I2C_PORT i2c0
#define I2C_FREQ 40000
#define ADS1115_I2C_ADDR 0x48
const uint8_t SDA_PIN = 8;
const uint8_t SCL_PIN = 9;

struct ads1115_adc adc;

int main(){
    stdio_init_all();
    printf("Hello world!\n");
    // Initialize I2C
    i2c_init(I2C_PORT, I2C_FREQ);
    gpio_set_function(SDA_PIN, GPIO_FUNC_I2C);
    gpio_set_function(SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(SDA_PIN);
    gpio_pull_up(SCL_PIN);

    // Initialize ADC
    ads1115_init(I2C_PORT, ADS1115_I2C_ADDR, &adc); // & is a pointer to instance

    // Configure the ADC. This is recording the signal at CH0. The
    // programmable gain amplifier (PGA) is set to default.
    // Setting the ADC rate to 860 SPS
    ads1115_set_input_mux(ADS1115_MUX_SINGLE_0, &adc);
    ads1115_set_pga(ADS1115_PGA_4_096, &adc);
    ads1115_set_data_rate(ADS1115_RATE_860_SPS, &adc);

    // Write the configuration to the ADS1115
    ads1115_write_config(&adc);

    // Declare channel 1 data container
    uint16_t adc_ch0;
    float volts_ch0;

    // Read and print the CH0 ADC value
    while(true){
        ads1115_read_adc(&adc_ch0, &adc);   // read ADC
        volts_ch0 = ads1115_raw_to_volts(adc_ch0, &adc);    // convert to volts
        printf("ADC CH0: %u Votlage: %1.3f\n", adc_ch0, volts_ch0);    // print

        sleep_us(10000); // print every 1.5 ms
    }

}