# Generated Cmake Pico project file

cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Initialise pico_sdk from installed location
# (note this can come from environment, CMake cache etc)

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
set(PICO_BOARD pico_w CACHE STRING "Board type")

# Pull in Raspberry Pi Pico SDK (must be before project)
include(pico_sdk_import.cmake)

project(write2SDcard C CXX ASM)

# Initialise the Raspberry Pi Pico SDK
pico_sdk_init()

# # Collect source files
# set(SD_LIB_PATH ${CMAKE_CURRENT_LIST_DIR}/lib/no-OS-FatFS-SD-SDIO-SPI-RPi-Pico)
# file(GLOB_RECURSE SD_LIB_SOURCES
#     ${SD_LIB_PATH}/src/*.c
#     ${SD_LIB_PATH}/FatFs_SPI/*.c
# )

# Add executable. Default name is the project name, version 0.1
add_executable(write2SDcard 
    write2SDcard.c
    hw_config.c
    ${SD_LIB_SOURCES}
    #lib/no-OS-FatFS-SD-SDIO-SPI-RPi-Pico/examples/simple/main.c
)

# Add PRINTF functionality for debugging
add_compile_definitions(USE_PRINTF)

# === SD Card Library Path ===
set(SD_LIB_PATH ${CMAKE_CURRENT_LIST_DIR}/lib/no-OS-FatFS-SD-SDIO-SPI-RPi-Pico)

# Collect source files from the library
file(GLOB_RECURSE SD_LIB_SOURCES
    ${SD_LIB_PATH}/src/*.c
    ${SD_LIB_PATH}/sd_driver/*.c
    ${SD_LIB_PATH}/sd_driver/SPI/*.c
)

# Add subdirectories
add_subdirectory(lib/no-OS-FatFS-SD-SDIO-SPI-RPi-Pico/src build)

# Set the program name and version
pico_set_program_name(write2SDcard "write2SDcard")
pico_set_program_version(write2SDcard "0.1")

# Modify the below lines to enable/disable output over UART/USB
pico_enable_stdio_uart(write2SDcard 0)
pico_enable_stdio_usb(write2SDcard 1)

# Add the standard library to the build
target_link_libraries(write2SDcard
        pico_stdlib
)

# Add the standard include files to the build
target_include_directories(write2SDcard PRIVATE
        ${CMAKE_CURRENT_LIST_DIR}
        ${SD_LIB_PATH}/include
        ${SD_LIB_PATH}/src
        ${SD_LIB_PATH}/src/include
        ${SD_LIB_PATH}/sd_driver
        ${SD_LIB_PATH}/sd_driver/SPI
)

# Add any user requested libraries
target_link_libraries(write2SDcard 
        hardware_spi
        no-OS-FatFS-SD-SDIO-SPI-RPi-Pico
)

pico_add_extra_outputs(write2SDcard)

