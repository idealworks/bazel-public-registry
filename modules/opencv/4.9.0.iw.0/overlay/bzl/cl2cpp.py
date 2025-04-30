import argparse
import glob
import hashlib
import os
import re
from pathlib import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "Converts a set of .cl files to a corresponsing cpp/hpp pair"
    )
    parser.add_argument(
        "module_name",
        help="Name of the opencv module in question, this name will be part of the output file's name",
        type=str,
    )
    parser.add_argument(
        "cl_dir", help="Path to a directory containing .cl scripts", type=str
    )
    parser.add_argument(
        "output",
        help="output file to be generated, extended with .cpp and .hpp",
        type=str,
    )

    args = parser.parse_args()

    if not Path(args.cl_dir).exists():
        raise ValueError(f"Path {args.cl_dir} does not exist")

    cl_files = glob.glob(f"{args.cl_dir}/*.cl")
    cl_files.sort()

    if not cl_files:
        raise ValueError(f"Can't find OpenCL kernels in directory: {args.cl_dir}")

    res_cpp = """// This file is auto-generated. Do not edit!

#include "opencv2/core.hpp"
#include "cvconfig.h"
#include "{}"

#ifdef HAVE_OPENCL

namespace cv
{{
namespace ocl
{{
namespace {}
{{

static const char* const moduleName = "{}";

""".format(
        args.output.split("/")[-1] + ".hpp", args.module_name, args.module_name
    )

    res_hpp = """// This file is auto-generated. Do not edit!

#include "opencv2/core/ocl.hpp"
#include "opencv2/core/ocl_genbase.hpp"
#include "opencv2/core/opencl/ocl_defs.hpp"

#ifdef HAVE_OPENCL

namespace cv
{{
namespace ocl
{{
namespace {}
{{

""".format(
        args.module_name
    )

    for file in cl_files:
        with open(file, "r", encoding="utf-8") as fp:
            lines = fp.read()
        filename = Path(file).stem
        lines += "\n"
        lines = lines.replace("\r", "")
        lines = lines.replace("\t", "  ")

        # remove multiline comments /* .... */
        lines = re.sub(r"/\*([^*]/|\*[^/]|[^*/])*\*/", "", lines, flags=re.DOTALL)
        # remove single comments /* .... */
        lines = re.sub(r"/\*([^\n])*\*/", "", lines, flags=re.DOTALL)
        # remove comments // till the end of the line
        lines = re.sub(r"[ ]*//[^\n]*\n", "\n", lines)
        # collapse multiple empty lines and leading spaces
        lines = re.sub(r"\n[ ]*(\n[ ]*)*", "\n", lines)
        # Remove leading newline
        lines = re.sub(r"^\n", "", lines)

        lines = lines.replace("\\", "\\\\")
        lines = lines.replace('"', '\\"')
        lines = lines.replace("\n", '\\n"\n"')

        # unneeded " at the end of file
        lines = re.sub('"$', "", lines)

        md5sum = hashlib.md5(lines.encode("utf-8")).hexdigest()
        res_cpp += """struct cv::ocl::internal::ProgramEntry {}_oclsrc={{moduleName, "{}",\n"{}, "{}", NULL}};\n""".format(
            filename, filename, lines, md5sum
        )
        res_hpp += "extern struct cv::ocl::internal::ProgramEntry {}_oclsrc;\n".format(
            filename
        )

    res_cpp += "\n}}}\n#endif\n"
    res_hpp += "\n}}}\n#endif\n"

    print(os.getcwd())
    print(f"Writing to {os.getcwd()}/{args.output}.cpp")
    with open(f"{args.output}.cpp", "w") as fp:
        fp.write(res_cpp)
    with open(f"{args.output}.hpp", "w") as fp:
        fp.write(res_hpp)
