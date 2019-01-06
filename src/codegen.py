#!/usr/bin/python

if __name__ == "__main__":
    import argparse
    import logging
    import sys

    try:
        args_parser = argparse.ArgumentParser(description="Generate code based on the input.")
        args_parser.add_argument("-o",  "--output", dest="output", default="", help="output file base name or empty (default) for stdout")
        args_parser.add_argument("-oh", "--output-header", dest="output_header", default="", help="output header file base name (overrides -o)")
        args_parser.add_argument("-os", "--output-source", dest="output_source", default="", help="output source file base name (overrides -o)")
        args_parser.add_argument("-i",  "--index", dest="index", default="", help="path to the index file")
        args_parser.add_argument("-l",  "--loglevel", dest="loglevel", default="WARNING", help="minimum logging level (DEBUG|INFO|WARNING|ERROR|CRITICAL)")

        args = args_parser.parse_args()

        # Setup logging if required.
        assert args.loglevel
        loglevel_str = args.loglevel.upper()
        if loglevel_str not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            print("Invalid log level, has to be on of DEBUG, INFO, WARNING, ERROR, CRITICAL.", file=sys.stderr)
            sys.exit(1)

        loglevel = getattr(logging, loglevel_str, None)
        assert loglevel is not None
        logging.basicConfig(stream=sys.stderr, level=loglevel, format="%(levelname)s %(message)s")

        # Prepare header and source output if not provided. The arguments are used later on by generator.
        if not args.output_header and args.output:
            args.output_header = args.output

        if not args.output_source and args.output:
            args.output_source = args.output

        # Read codemodel's class diagram from the input.
        import codemodel
        raw_data = sys.stdin.read()
        logging.debug("Input data: " + raw_data)
        class_diag = codemodel.from_json(raw_data)

        # Run a code generator (only C++ for now).
        from codegen.cpp import Generator as CppGenerator
        CppGenerator().run(class_diag, args)
    finally:
        logging.shutdown()
#endif __main__
