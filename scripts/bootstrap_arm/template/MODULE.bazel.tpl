module(
    name = "arm_gnu_toolchain_linux_x86_64_aarch64_none_linux_gnu",
    version = "@@VERSION@@",
)

bazel_dep(name = "rules_cc", version = "0.1.1")
bazel_dep(name = "platforms", version = "0.0.11")
