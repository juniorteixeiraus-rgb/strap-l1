cmake_minimum_required(VERSION 3.15)
project(strap-pouw LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenSSL REQUIRED)

add_library(strap-pouw STATIC strap-pouw.cpp)
target_include_directories(strap-pouw PUBLIC ${OPENSSL_INCLUDE_DIR})
target_link_libraries(strap-pouw OpenSSL::SSL OpenSSL::Crypto)

install(TARGETS strap-pouw ARCHIVE DESTINATION .)
