load("@rules_cc//cc:find_cc_toolchain.bzl", "find_cc_toolchain")

def _generate_list_txt_impl(ctx):
    toolchain = find_cc_toolchain(ctx)

    preprocessor = None
    clang_flags = ""

    # | Toolchain has | Result                           |
    # |---------------|----------------------------------|
    # | cpp only      | uses cpp, breaks immediately     |
    # | clang only    | uses clang, loop ends naturally  |
    # | clang then cpp| clang set, cpp overwrites, breaks|
    # | cpp then clang| cpp set, breaks, clang skipped   |
    # | neither       | preprocessor = None, fail()      |

    for file in toolchain._compiler_files.to_list():
        if file.basename == "clang" or file.basename.endswith("-clang"):
            preprocessor = file.path
            clang_flags = "-E -x c"

        # preprocessor_executable in bazel 8.x points to <toolchain_buildfile_path>/cpp
        # This is not the case for cross compiling toolchains where the binary e.g. may really be
        # <toolchain_buildfile_path>/bin/aarch64-linux-gnu-cpp
        # So loop on all the files in the compiler files and find the one which basename ends with cpp and
        # use it
        if file.basename.endswith("cpp"):
            preprocessor = file.path
            break

    if not preprocessor:
        fail("Could not find a C preprocessor in the toolchain.Expected a file ending in 'cpp' (GCC) or named 'clang' (LLVM) in the compiler files.")

    output_txt = ctx.actions.declare_file(ctx.attr.output_txt)
    script_args = ""
    for arg in ctx.files.script_args:
        script_args += arg.path + " "

    ctx.actions.run_shell(
        outputs = [output_txt],
        inputs = ctx.files.script_args + toolchain._compiler_files.to_list(),
        tools = [ctx.file.script],
        command = "{script} '{pp} {flags}' {args} > {out}".format(
            script = ctx.executable.script.path,
            pp = preprocessor,
            flags = clang_flags,
            args = script_args,
            out = output_txt.path,
        ),
    )
    return [DefaultInfo(files = depset([output_txt]))]

generate_list_txt = rule(
    implementation = _generate_list_txt_impl,
    attrs = {
        "script": attr.label(mandatory = True, allow_single_file = True, executable = True, cfg = "exec"),
        "output_txt": attr.string(mandatory = True),
        "script_args": attr.label_list(allow_files = True),
        "data": attr.label_list(allow_files = True),
    },
    toolchains = ["@rules_cc//cc:toolchain_type"],
)
