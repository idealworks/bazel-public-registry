def _generate_dispatched_files(ctx):
    """Generates SIMD-specific source files based on CPU optimizations."""
    filename = ctx.attr.name
    optimizations = ctx.attr.optimizations
    output_files = []

    dispatch_modes = ["BASELINE"]
    declarations_str = """#define CV_CPU_SIMD_FILENAME "{}.simd.hpp"
""".format(filename)

    for opt in optimizations:
        opt_lower = opt.lower()
        output_file = ctx.actions.declare_file("{}.{}.cpp".format(filename, opt_lower))

        # Generate the SIMD-specific source file
        content = """#include "precomp.hpp"
#include "{}.simd.hpp"
""".format(filename)

        ctx.actions.write(output_file, content)
        output_files.append(output_file)

        dispatch_modes.insert(0, opt)
        declarations_str += """#define CV_CPU_DISPATCH_MODE {}
#include "opencv2/core/private/cv_cpu_include_simd_declarations.hpp"
""".format(opt)

    declarations_str += """#define CV_CPU_DISPATCH_MODES_ALL {}
#undef CV_CPU_SIMD_FILENAME
""".format(", ".join(dispatch_modes))

    # Generate the SIMD declarations header
    declarations_file = ctx.actions.declare_file("{}.simd_declarations.hpp".format(filename))
    ctx.actions.write(declarations_file, declarations_str)

    return [
        DefaultInfo(files = depset(output_files + [declarations_file])),
        CcInfo(
            compilation_context = cc_common.create_compilation_context(
                headers = depset([declarations_file]),
            ),
        ),
    ]

ocv_dispatched_file = rule(
    implementation = _generate_dispatched_files,
    attrs = {
        "optimizations": attr.string_list(mandatory = True),
    },
)

def get_common_dir_name(srcs):
    dir_names = [file.dirname for file in srcs]
    ref = dir_names[0]
    for dir_name in dir_names:
        if dir_name != ref:
            fail("opencl files should be in the same directory, {} does not match {}".format(dir_name, ref))
    return ref

def _cl_to_cpp(ctx):
    dir_name = get_common_dir_name(ctx.files.srcs)

    out_cpp = ctx.actions.declare_file("{}.cpp".format(ctx.attr.output_name))
    out_hpp = ctx.actions.declare_file("{}.hpp".format(ctx.attr.output_name))

    ctx.actions.run(
        inputs = ctx.files.srcs,
        outputs = [out_cpp, out_hpp],
        executable = ctx.executable._generator_script,
        arguments = [ctx.attr.module_name, dir_name, "{}/{}".format(out_cpp.dirname, ctx.attr.output_name)],
        mnemonic = "ClToCpp",
        progress_message = "Generating cpp files for %{label}",
    )
    return [
        DefaultInfo(files = depset([out_cpp, out_hpp])),
        CcInfo(
            compilation_context = cc_common.create_compilation_context(
                headers = depset([out_hpp]),
                includes = depset([out_hpp.dirname]),
            ),
        ),
    ]

cl_to_cpp = rule(
    implementation = _cl_to_cpp,
    attrs = {
        "module_name": attr.string(mandatory = True),
        "srcs": attr.label_list(mandatory = True, allow_empty = False, allow_files = True),
        "output_name": attr.string(mandatory = True),
        "_generator_script": attr.label(
            default = Label("//bzl:cl_to_cpp"),
            executable = True,
            cfg = "exec",
        ),
    },
)
