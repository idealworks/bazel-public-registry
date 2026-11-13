""" Implements a macro for setting up a rosbridge websocket server.
"""

load("@rules_python//python:defs.bzl", "py_binary")

def ros2_rosbridge(name, py_idl_deps, **kwargs):
    """ Defines a rosbridge websocket server for a set of interfaces.

    rosbridge imports message/service/action types by name at runtime, so every interface
    its clients use must be a dep of the binary.

    Args:
        name: A unique target name.
        py_idl_deps: A list of Python IDL libraries (py_ros2_interface_library targets)
            served by the bridge.
        **kwargs: https://bazel.build/reference/be/common-definitions#common-attributes-binaries
    """
    deps = [
        Label("//rosbridge_server"),
        Label("//rosbridge_library"),
        Label("//rosbridge_msgs:py_rosbridge_msgs"),
        Label("@ros2_rclpy//:rclpy"),
    ]

    # Callers may pass their full interface list, which can already contain rosbridge_msgs.
    deps += [d for d in py_idl_deps if native.package_relative_label(d) not in deps]
    py_binary(
        name = name,
        srcs = [Label("//rosbridge_server:scripts/rosbridge_websocket.py")],
        main = Label("//rosbridge_server:scripts/rosbridge_websocket.py"),
        deps = deps,
        **kwargs
    )
