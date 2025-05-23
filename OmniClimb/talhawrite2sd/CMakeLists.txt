# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.1.1)
set(toolchainVersion 14_2_Rel1)
set(picotoolVersion 2.1.1)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================
set(PICO_BOARD pico CACHE STRING "Board type")

cmake_minimum_required(VERSION 3.13)

# Import the Raspberry Pi Pico SDK
include(pico_sdk_import.cmake)

# Set project name and language
project(write2SDcard C CXX ASM)

# Set language standards
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# Initialize the Pico SDK
pico_sdk_init()

# === SD Card Library Path ===
set(SD_LIB_PATH ${CMAKE_CURRENT_LIST_DIR}/lib/no-OS-FatFS-SD-SDIO-SPI-RPi-Pico)

# Collect source files (.c and .cpp only)
file(GLOB_RECURSE SD_LIB_SOURCES
    ${SD_LIB_PATH}/include/FsLib/*.cpp
    ${SD_LIB_PATH}/include/iostream/*.cpp
    ${SD_LIB_PATH}/src/sd_driver/*.c
    ${SD_LIB_PATH}/src/sd_driver/SPI/*.c
    ${SD_LIB_PATH}/src/sd_driver/SDIO/*.c
    ${SD_LIB_PATH}/src/src/*.c
    ${SD_LIB_PATH}/src/src/*.cpp
)

# Define your executable and add sources
add_executable(write2SDcard
    write2SDcard.c
    hw_config.c
    ${SD_LIB_SOURCES}
)

target_include_directories(write2SDcard PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}
    ${SD_LIB_PATH}/include
    ${SD_LIB_PATH}/include/FsLib
    ${SD_LIB_PATH}/include/iostream
    ${SD_LIB_PATH}/src/include
    ${SD_LIB_PATH}/src/sd_driver
    ${SD_LIB_PATH}/src/sd_driver/SPI
    ${SD_LIB_PATH}/src/sd_driver/SDIO
)

# Link required Pico and hardware libraries
target_link_libraries(write2SDcard
    pico_stdlib
    hardware_spi
)

# Enable USB output, disable UART output
pico_enable_stdio_usb(write2SDcard 1)
pico_enable_stdio_uart(write2SDcard 0)

# Generate UF2, bin, and other output formats
pico_add_extra_outputs(write2SDcard)
