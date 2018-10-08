#!/usr/bin/python

if __name__ == "__main__":
    import argparse
    import codegen
    import codemodel
    import sys

    args_parser = argparse.ArgumentParser(description="Generate code based on the input.")
    args_parser.add_argument("-o", "--output", dest="output", default="", help="output file base name or empty (default) for stdout")
    args_parser.add_argument("-l", "--logmask", dest="logmask", default="EWI", help="log messages mask to be outputted to the stderr ('EWI' by default)")

    args = args_parser.parse_args()

    raw_data = sys.stdin.read()
    #print(raw_data) TODO Add debugging option.
    class_diag = codemodel.from_json(raw_data)

    gen = codegen.cpp.Generator(args)
    class_diag.accept(gen)
#endif __main__
