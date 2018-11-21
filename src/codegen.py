#!/usr/bin/python

if __name__ == "__main__":
    import argparse
    import codegen
    import codemodel
    import sys

    args_parser = argparse.ArgumentParser(description="Generate code based on the input.")
    args_parser.add_argument("-o",  "--output", dest="output", default="", help="output file base name or empty (default) for stdout")
    args_parser.add_argument("-oh", "--output-header", dest="output_header", default="", help="output header file base name (overrides -o)")
    args_parser.add_argument("-os", "--output-source", dest="output_source", default="", help="output source file base name (overrides -o)")
    args_parser.add_argument("-i",  "--index", dest="index", default="", help="path to the index file")
    args_parser.add_argument("-l",  "--logmask", dest="logmask", default="EWI", help="log messages mask to be outputted to the stderr ('EWI' by default)")

    args = args_parser.parse_args()

    if not args.output_header and args.output:
        args.output_header = args.output

    if not args.output_source and args.output:
        args.output_source = args.output

    raw_data = sys.stdin.read()
    #print(raw_data) TODO Add debugging option.
    class_diag = codemodel.from_json(raw_data)

    gen = codegen.cpp.Generator(args)
    gen.run(class_diag)
#endif __main__
