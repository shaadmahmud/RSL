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

// Declare sampling time constants
const uint64_t conv_wait = 1300;    // conversion wait time in microseconds
uint64_t Ts = 20000 - 4*conv_wait;    // sampling interval in microseconds

struct ads1115_adc adc;

int main(){
    stdio_init_all();
    
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
    // ads1115_set_input_mux(ADS1115_MUX_SINGLE_2, &adc);
    ads1115_set_pga(ADS1115_PGA_4_096, &adc);
    ads1115_set_data_rate(ADS1115_RATE_860_SPS, &adc);

    // Write the configuration to the ADS1115
    ads1115_write_config(&adc);

    // Declare channel data containers
    uint16_t adc_ch0;
    uint16_t adc_ch1;
    uint16_t adc_ch2;
    uint16_t adc_ch3;
    float volts_ch0;
    float volts_ch1;
    float volts_ch2;
    float volts_ch3;

    // Declare timing data containers
    absolute_time_t t_start;
    absolute_time_t t_end;
    uint64_t t_stamp;

    // Read and print the CH0 ADC value
    while(true) {
        t_start = get_absolute_time();  // get start of conversion time

        // Configure CH0 conversion
        ads1115_set_input_mux(ADS1115_MUX_SINGLE_0, &adc);
        ads1115_read_adc(&adc_ch0, &adc);   // read CH0
        sleep_us(conv_wait);

        // Configure CH1 conversion
        ads1115_set_input_mux(ADS1115_MUX_SINGLE_1, &adc);
        ads1115_read_adc(&adc_ch1, &adc);   // read CH1
        sleep_us(conv_wait);

        // Configure CH2 conversion
        ads1115_set_input_mux(ADS1115_MUX_SINGLE_2, &adc);
        ads1115_read_adc(&adc_ch2, &adc);   // read CH2
        sleep_us(conv_wait);

        // Configure CH3 conversion
        ads1115_set_input_mux(ADS1115_MUX_SINGLE_3, &adc);
        ads1115_read_adc(&adc_ch3, &adc);   // read CH3
        sleep_us(conv_wait);
        
        t_end = get_absolute_time();    // get end of conversion time

        t_stamp = absolute_time_diff_us(t_start, t_end);    // compute the time it took to perform conversions

        // Convert ADC values to volts
        volts_ch0 = ads1115_raw_to_volts(adc_ch0, &adc);    // convert to volts
        volts_ch1 = ads1115_raw_to_volts(adc_ch1, &adc);    // convert to volts
        volts_ch2 = ads1115_raw_to_volts(adc_ch2, &adc);    // convert to volts
        volts_ch3 = ads1115_raw_to_volts(adc_ch3, &adc);    // convert to volts

        // Print time stamp voltage values to terminal
        printf("%lld  |   %1.3f   |   %1.3f   |   %1.3f   |   %1.3f\n",
            t_stamp, volts_ch0, volts_ch1, volts_ch2, volts_ch3
        );

        sleep_us(Ts);

    }

}