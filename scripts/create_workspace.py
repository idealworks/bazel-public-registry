"""Create a workspace based on a profile"""

#!/bin/env python

import argparse
from pathlib import Path

from add_module_to_ws import add_module_to_ws

# ROS packages in base and bpr at the same time
ROS_BASE_JAZZY_PKGS = {
    "ros2_class_loader": "ros/class_loader",
    "ros2_common_interfaces": "ros2/common_interfaces",
    "ros2_launch": "ros2/launch",
    "ros2_launch_ros": "ros2/launch_ros",
    "ros2_pluginlib": "ros/pluginlib",
    "ros2_rclcpp": "ros2/rclcpp",
    "ros2_rclpy": "ros2/rclpy",
    "cyclonedds": "eclipse-cyclonedds/cyclonedds",
    "ros2_rmw_cyclonedds": "ros2/rmw_cyclonedds",
}

# ROS packages in core and bpr at the same time
ROS_CORE_JAZZY_PKGS = {
    **ROS_BASE_JAZZY_PKGS,
    "ros2_geometry2": "ros2/geometry2",
    "ros2_kdl_parser": "ros/kdl_parser",
    "ros2_robot_state_publisher": "ros/robot_state_publisher",
    "ros2_rosbag2": "ros2/rosbag2",
    "ros2_urdf": "ros2/urdf",
}

# Ros packages built in bazel, used as deps of core,
# available in ros2.repos, but not in CORE or BASE
ROS_DEPS_JAZZY_PKGS = {
    "console_bridge": "ros2/console_bridge_vendor",
    "iceoryx": "eclipse-iceoryx/iceoryx",
    "osrf_pycommon": "osrf/osrf_pycommon",
    "orocos_kdl": "ros2/orocos_kdl_vendor",
    "ros2cli": "ros2/ros2cli",
    "ros2_ament_index": "ament/ament_index",
    "ros2_keyboard_handler": "ros-tooling/keyboard_handler",
    "ros2_libstatistics_collector": "ros-tooling/libstatistics_collector",
    "ros2_message_filters": "ros2/message_filters",
    "ros2_rcl": "ros2/rcl",
    "ros2_rmw": "ros2/rmw",
    "ros2_rmw_implementation": "ros2/rmw_implementation",
    "ros2_rmw_dds_common": "ros2/rmw_dds_common",
    "ros2_rcutils": "ros2/rcutils",
    "ros2_rcpputils": "ros2/rcpputils",
    "ros2_rcl_interfaces": "ros2/rcl_interfaces",
    "ros2_rcl_logging": "ros2/rcl_logging",
    "ros2_rosidl": "ros2/rosidl",
    "ros2_rosidl_runtime_py": "ros2/rosidl_runtime_py",
    "ros2_rosidl_typesupport": "ros2/rosidl_typesupport",
    "ros2_rosidl_python": "ros2/rosidl_python",
    "ros2_rpyutils": "ros2/rpyutils",
    "ros2_tracing": "ros2/ros2_tracing",
    "ros2_urdfdom": "ros/urdfdom",
    "ros2_urdfdom_headers": "ros/urdfdom_headers",
    "ros2_unique_identifier_msgs": "ros2/unique_identifier_msgs",
    "tinyxml2": "ros2/tinyxml2_vendor",
}

# ROS packages built in bazel, not dependencies of core, and available in
# ros2/ros2.repos
ROS_EXTRA_JAZZY_PKGS = {
    "ros2_ament_cmake_ros": "ros2/ament_cmake_ros",
    "ros2_image_common": "ros-perception/image_common",
    "ros2_resource_retriever": "ros/resource_retriever",
    "ros2_rosidl_dynamic_typesupport": "ros2/rosidl_dynamic_typesupport",
    "ros2_test_interface_files": "ros2/test_interface_files",
    "ros2_demo_nodes_py": "ros2/demos",
    "ros2_laser_geometry": "ros-perception/laser_geometry",
}

# ROS packages in bpr but not in ros2.repos containing ros2 in their names
ROS_PACKAGES_NOT_IN_ROS2_REPOS = {
    "com_github_mvukov_rules_ros2": {
        "url": "https://github.com/eddygharib/rules_ros2/",
        "tag": "1.0.0.eddy.1",
    },
    "ros2_angles": {"url": "https://github.com/ros/angles", "tag": "1.16.0"},
    "ros2_diagnostics": {
        "url": "https://github.com/ros/diagnostics/",
        "branch": "ros2-jazzy",
    },
    "ros2_gps_umd": {
        "url": "https://github.com/swri-robotics/gps_umd",
        "branch": "ros2-devel",
    },
    "ros2_nav2": {
        "url": "https://github.com/ros-navigation/navigation2",
        "branch": "jazzy",
    },
    "ros2_xacro": {"url": "https://github.com/ros/xacro", "tag": "2.0.9"},
    "ros2_laser_scan_matcher": {
        "url": "https://github.com/AlexKaravaev/ros2_laser_scan_matcher",
        "branch": "main",
    },
    "ros2_rosbridge_suite": {
        "url": "https://github.com/RobotWebTools/rosbridge_suite",
        "branch": "jazzy",
    },
    "ros2_rosx_introspection": {
        "url": "https://github.com/facontidavide/rosx_introspection",
        "branch": "master",
    },
}
MODULES_OF_INTEREST_MAP = {
    "ros2": list(ROS_CORE_JAZZY_PKGS.keys())
    + list(ROS_DEPS_JAZZY_PKGS.keys())
    + list(ROS_EXTRA_JAZZY_PKGS.keys())
    + list(ROS_PACKAGES_NOT_IN_ROS2_REPOS.keys()),
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Creates a workspace based on a profile"
    )
    parser.add_argument("ws_path", help="Target path to create the ws at", type=str)
    parser.add_argument(
        "registry_path",
        help="Path to the registry from which the ws will be created",
        type=str,
    )
    parser.add_argument(
        "profile", choices=["global", "ros2"], help="profile to generate the ws"
    )
    args = parser.parse_args()

    ws_path = Path(args.ws_path)
    registry_path = Path(args.registry_path)

    ws_path.mkdir(exist_ok=True)

    modules_of_interest = []
    if args.profile == "global":
        modules_of_interest = [
            p.name for p in (registry_path / "modules").iterdir() if p.is_dir()
        ]
    else:
        modules_of_interest = MODULES_OF_INTEREST_MAP[args.profile]

    for module_name in modules_of_interest:
        add_module_to_ws(module_name, registry_path, ws_path)
