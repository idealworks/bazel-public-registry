#pragma once

// Mirrors the header ament_generate_version_header() writes for the CMake build
#define RCLCPP_VERSION_MAJOR 28
#define RCLCPP_VERSION_MINOR 1
#define RCLCPP_VERSION_PATCH 23
#define RCLCPP_VERSION_STR "28.1.23"

/// True when this rclcpp is at least major.minor.patch
#define RCLCPP_VERSION_GTE(major, minor, patch) ( \
    (major < RCLCPP_VERSION_MAJOR) ? true \
    : ((major > RCLCPP_VERSION_MAJOR) ? false \
    : ((minor < RCLCPP_VERSION_MINOR) ? true \
    : ((minor > RCLCPP_VERSION_MINOR) ? false \
    : ((patch < RCLCPP_VERSION_PATCH) ? true \
    : ((patch > RCLCPP_VERSION_PATCH) ? false \
    : true))))))
