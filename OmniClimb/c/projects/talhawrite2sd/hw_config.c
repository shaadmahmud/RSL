
/* hw_config.c
Copyright 2021 Carl John Kugler III

Licensed under the Apache License, Version 2.0 (the License); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at

   http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an AS IS BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
*/

/*
This file should be tailored to match the hardware design.

See
https://github.com/carlk3/no-OS-FatFS-SD-SDIO-SPI-RPi-Pico/tree/main#customizing-for-the-hardware-configuration
*/

#include "lib/no-OS-FatFS-SD-SDIO-SPI-RPi-Pico/src/include/hw_config.h"

/* Configuration of hardware SPI object */
static spi_t spi = {
    .hw_inst = spi1,     // Changed from spi1 to spi0
    .sck_gpio = 10,      // Changed from 10 to 18
    .mosi_gpio = 11,     // Changed from 11 to 19
    .miso_gpio = 8,     // Changed from 12 to 16
    .baud_rate = 125 * 1000 * 1000 / 4  // 31.25 MHz (can adjust as needed)
};

/* SPI Interface */
static sd_spi_if_t spi_if = {
    .spi = &spi,
    .ss_gpio = 9   // Changed from 13 to 17
};

/* Configuration of the SD Card socket object */
static sd_card_t sd_card = {
    .type = SD_IF_SPI,
    .spi_if_p = &spi_if
};

size_t sd_get_num() {
    return 1;
}

sd_card_t *sd_get_by_num(size_t num) {
    if (0 == num) {
        return &sd_card;
    } else {
        return NULL;
    }
}
