cmake_minimum_required(VERSION 2.8)

SET(COMPILE_DEFINITIONS -Werror)

include_directories(/opt/vc/include)
include_directories(/opt/vc/include/interface/vcos/pthreads)
include_directories(/opt/vc/include/interface/vmcs_host)
include_directories(/opt/vc/include/interface/vmcs_host/linux)

link_directories(/opt/vc/lib)

add_executable(raspicap raspicap.cpp)

find_package( OpenCV REQUIRED )

target_link_libraries(raspicap mmal_core mmal_util mmal_vc_client vcos bcm_host cairo ${OpenCV_LIBS} pthread rt m)

