load("@rules_cc//cc:find_cc_toolchain.bzl", "find_cc_toolchain", "use_cc_toolchain")

def _generate_list_txt_impl(ctx):
    toolchain = find_cc_toolchain(ctx)

    cpp_tool = toolchain.preprocessor_executable

    # preprocessor_executable in bazel 8.x points to <toolchain_buildfile_path>/cpp
    # This is not the case for cross compiling toolchains where the binary e.g. may really be
    # <toolchain_buildfile_path>/bin/aarch64-linux-gnu-cpp
    # So loop on all the files in the compiler files and find the one which basename ends with cpp and
    # use it
    for file in toolchain._compiler_files.to_list():
        if file.basename.endswith("cpp"):
            cpp_tool = file.path

    output_txt = ctx.actions.declare_file(ctx.attr.output_txt)
    script_args = ""
    for arg in ctx.files.script_args:
        script_args += arg.path + " "

    ctx.actions.run_shell(
        outputs = [output_txt],
        inputs = ctx.files.script_args + toolchain._compiler_files.to_list(),
        tools = [ctx.file.script],
        command = "{} {} {} > {}".format(ctx.executable.script.path, cpp_tool, script_args, output_txt.path),
    )
    return [DefaultInfo(files = depset([output_txt]))]

generate_list_txt = rule(
    implementation = _generate_list_txt_impl,
    attrs = {
        "script": attr.label(mandatory = True, allow_single_file = True, executable = True, cfg = "host"),
        "output_txt": attr.string(mandatory = True),
        "script_args": attr.label_list(allow_files = True),
        "data": attr.label_list(allow_files = True),
    },
    toolchains = ["@rules_cc//cc:toolchain_type"],
)
