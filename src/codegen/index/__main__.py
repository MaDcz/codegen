from .module import *

if __name__ == "__main__":
    import argparse

    args_parser = argparse.ArgumentParser(description="Utility for maintaining a codegen index.")
    args_parser.add_argument("index", metavar="INDEX", help="Path to the index file.")
    args_parser.add_argument("command", metavar="COMMAND", help="Available commands: add_cpp_include, clear.")
    args_parser.add_argument("command_args", metavar="COMMAND_ARG", nargs="*")

    args = args_parser.parse_args()

    command = None
    if args.command == "add_cpp_include":

        def add_cpp_include(index, command_args):
            if len(command_args) != 2:
                raise RuntimeError("The 'add_cpp_include' command expects exactly two arguments, full type and the source where to find it.")

            full_type_str = command_args[0]
            full_type = tuple(full_type_str.split("::")) # TODO Do it in a more robust way. Remove empty items from the beggining and end, check that it isn't empty. Maybe support more serparators than C++ '::' to allow some universal notation, like split on characters that arent allowed in a namespace or type name.
            include = command_args[1]

            if full_type in index:
                raise RuntimeError("Type '{}' already present in the index.".format(full_type_str))

            index[full_type] = {"cpp": {"include": include }}
        #enddef
        command = add_cpp_include

    elif args.command == "clear":

        def clear(index, command_args):
            index.clear()
        #enddef
        command = clear

    else:
        raise RuntimeError("Invalid command '{}'.".format(args.command))

    assert command is not None

    index_file = IndexFile(args.index)
    with index_file.lock():
        index = index_file.load()
        command(index, args.command_args)
        index_file.save(index)
#endif __main__
