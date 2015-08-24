
FUSEKIT_DIR=fusekit-0.6.5

NRF_DIR = nRF24
NRF_SOURCES = $(NRF_DIR)/bcm2835.c $(NRF_DIR)/RF24.cpp
NRF_DEPS = $(NRF_DIR)/bcm2835.h \
  $(NRF_DIR)/RF24.h \
  $(NRF_DIR)/RF24_config.h \
  $(NRF_DIR)/nRF24L01.h

SOURCES = carlink.cpp $(NRF_SOURCES)

CPPFLAGS = -D_FILE_OFFSET_BITS=64 -I/usr/include/fuse \
   -I$(NRF_DIR) \
   -I$(FUSEKIT_DIR)/include -DFUSE_USE_VERSION=27
LDFLAGS = -Lfusekit

carlink: $(SOURCES) $(NRF_DEPS)
	g++ $(SOURCES) -o $@ $(CPPFLAGS) $(LDFLAGS) -lfuse
