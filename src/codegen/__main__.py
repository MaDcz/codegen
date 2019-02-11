if __name__ == "__main__":
    import argparse
    import logging
    import sys

    try:
        args_parser = argparse.ArgumentParser(description="Generate code based on the input.")
        args_parser.add_argument("-o",  "--output", dest="output", default="", help="output file base name or empty (default) for stdout")
        args_parser.add_argument("-oh", "--output-header", dest="output_header", default="", help="output header file name (overrides -o)")
        args_parser.add_argument("-os", "--output-source", dest="output_source", default="", help="output source file name (overrides -o)")
        args_parser.add_argument("-i",  "--index", dest="index", default="", help="path to the index file")
        args_parser.add_argument("-l",  "--loglevel", dest="loglevel", default="WARNING", help="minimum logging level (DEBUG|INFO|WARNING|ERROR|CRITICAL)")
        args_parser.add_argument("input_files", metavar="INPUT_FILE", nargs="*")

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

        # Read codemodel's class diagram from the input.
        import codemodel

        def process_input_file(f, args):
            raw_data = f.read()
            logging.debug("Input data: " + raw_data)
            class_diag = codemodel.from_json(raw_data)

            # Run a code generator (only C++ for now).
            from codegen.cpp import Generator as CppGenerator
            # TODO This won't most probably work with multiple inputs.
            CppGenerator().run(class_diag, args)

        if args.input_files:
            for input_filepath in args.input_files:
                if input_filepath.strip() == "-":
                    process_input_file(sys.stdin, args)
                else:
                    logging.debug("Processing input file '{}'.".format(input_filepath))
                    with open(input_filepath, "r") as f:
                        process_input_file(f, args)
        else:
            process_input_file(sys.stdin, args)

    finally:
        logging.shutdown()
#endif __main__
