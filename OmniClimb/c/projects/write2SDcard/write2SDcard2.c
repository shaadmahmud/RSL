#include <stdio.h>
#include "pico/stdlib.h"
#include "sd_card.h"
#include "f_util.h"
#include "ff.h"

// SPI Defines
#define SPI_PORT spi1
#define PIN_MISO 8
#define PIN_CS   9
#define PIN_SCK  10
#define PIN_MOSI 11

FATFS fs;
FIL fil;
FRESULT fr;
UINT bw;

int main() {
    stdio_init_all();

    // Initialize SPI pins
    spi_init(SPI_PORT, 1000 * 1000); // 1 MHz
    gpio_set_function(PIN_MISO, GPIO_FUNC_SPI);
    gpio_set_function(PIN_CS,   GPIO_FUNC_SIO);
    gpio_set_function(PIN_SCK,  GPIO_FUNC_SPI);
    gpio_set_function(PIN_MOSI, GPIO_FUNC_SPI);
    gpio_set_dir(PIN_CS, GPIO_OUT);
    gpio_put(PIN_CS, 1);  // Chip select inactive (high)

    sleep_ms(1000); // Wait for SD card power stabilization

    // Initialize SD card
    if (!sd_init_driver()) {
        printf("ERROR: SD card initialization failed.\n");
        return -1;
    }
    printf("SD card initialized.\n");

    // Mount filesystem
    fr = f_mount(&fs, "", 1);
    if (fr != FR_OK) {
        printf("ERROR: f_mount failed (%d)\n", fr);
        return -2;
    }

    // Open or create file for writing
    fr = f_open(&fil, "test.txt", FA_WRITE | FA_CREATE_ALWAYS);
    if (fr != FR_OK) {
        printf("ERROR: f_open failed (%d)\n", fr);
        return -3;
    }

    while (true) {
        // Write to file
        const char *text = "Hello, SD card!\r\n";
        fr = f_write(&fil, text, strlen(text), &bw);
        if (fr != FR_OK || bw != strlen(text)) {
            printf("ERROR: f_write failed (%d)\n", fr);
        } else {
            printf("Wrote to SD: %s", text);
        }

        // Flush buffer to disk
        f_sync(&fil);

        sleep_ms(1000);
    }

    // f_close(&fil);  // Optional: unreachable due to infinite loop
    // f_mount(NULL, "", 0);  // Optional unmount

    return 0;
}

