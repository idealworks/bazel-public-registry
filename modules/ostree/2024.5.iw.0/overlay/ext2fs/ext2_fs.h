#pragma once

#include <sys/ioctl.h>

#define EXT2_IMMUTABLE_FL       0x00000010
#define EXT2_IOC_GETFLAGS       _IOR('f', 1, long)
#define EXT2_IOC_SETFLAGS       _IOW('f', 2, long)