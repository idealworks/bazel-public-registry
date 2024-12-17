"Utilities to use osrf_testing_tools_cpp in tests."

load("@rules_cc//cc:defs.bzl", "cc_test")


def memory_tools_cc_test(**kwargs):
    """
    Macro that adds the memory_tools_interpose shared library and the necessary
    environment variables to run a test with memory checking enabled.
    """

    env = kwargs.pop("env", {})
    env["LD_PRELOAD"] = "$(rootpath " + str(Label("//:memory_tools_interpose")) + ")"

    deps = kwargs.pop("deps", [])
    deps.append(Label("//:memory_tools"))

    data = kwargs.pop("data", [])
    data.append(Label("//:memory_tools_interpose"))

    cc_test(
        env = env,
        deps = deps,
        data = data,
        **kwargs,
    )
