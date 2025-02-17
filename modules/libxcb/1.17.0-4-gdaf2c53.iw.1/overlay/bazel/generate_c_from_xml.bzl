def _generate_c_from_xml_impl(ctx):
    # Iterate over each XML file and generate a corresponding .c file
    outputs = []
    for xml in ctx.files.srcs:
        c_file = ctx.actions.declare_file(xml.basename.replace(".xml", ".c"))
        h_file = ctx.actions.declare_file(xml.basename.replace(".xml", ".h"))
        outputs.append(c_file)
        outputs.append(h_file)

        # Construct the command
        args = [
            "-c",
            ctx.attr.package_string,
            "-l",
            ctx.attr.xorg_man_page,
            "-s",
            ctx.attr.lib_man_suffix,
            "-p",
            ctx.attr.xcb_python_dir,
        ]
        if ctx.attr.extra_args:
            args.extend(ctx.attr.extra_args)

        args.append(xml.path)

        # Run the Python script
        ctx.actions.run(
            inputs = ctx.files.srcs,
            outputs = [c_file, h_file],
            arguments = args,
            executable = ctx.executable._c_client_py,
            env = {
                "OUTPUT_PATH_PREFIX": c_file.dirname,
            },
        )

    return [DefaultInfo(files = depset(outputs))]

generate_c_from_xml = rule(
    implementation = _generate_c_from_xml_impl,
    attrs = {
        "srcs": attr.label_list(
            allow_files = [".xml"],
            mandatory = True,
            doc = "List of XML source files",
        ),
        "_c_client_py": attr.label(
            default = Label("//:c_client"),
            executable = True,
            cfg = "exec",
            doc = "Default c_client.py script",
        ),
        "package_string": attr.string(
            mandatory = True,
            doc = "Package string for the generated files",
        ),
        "xorg_man_page": attr.string(
            mandatory = True,
            doc = "X.Org man page reference",
        ),
        "lib_man_suffix": attr.string(
            mandatory = True,
            doc = "Library manual section suffix",
        ),
        "xcb_python_dir": attr.string(
            mandatory = True,
            doc = "XCB Python module directory",
        ),
        "extra_args": attr.string_list(
            mandatory = False,
            doc = "Additional arguments for c_client.py",
        ),
    },
)
