from .module import *

if __name__ == "__main__":
    import argparse

    args_parser = argparse.ArgumentParser(description="Utility for maintaining a codegen index.")
    args_parser.add_argument("index", metavar="INDEX", help="Path to the index file.")
    args_parser.add_argument("command", metavar="COMMAND", help="Available commands: add_cpp_include, clear.")
    args_parser.add_argument("command_args", metavar="COMMAND_ARG", nargs="*")

    args = args_parser.parse_args()

    command = None

    if args.command == "set_cpp_include":

        def set_cpp_include(index_file, command_args):
            if len(command_args) != 2:
                raise RuntimeError("The 'set_cpp_include' command expects exactly two arguments, full type and the source where to find it.")

            full_type_str = command_args[0]
            include = command_args[1]

            index = index_file.load()
            d = index.ensure(full_type_str, "cpp")
            if "include" not in d:
                d["include"] = include
                index_file.save(index)
            elif d["include"] != include:
                raise RuntimeError("C++ include already present in index for type '{}' and differs. ('{}' != '{}')".format(full_type_str, include, d["include"]))
        #enddef
        command = set_cpp_include

    elif args.command == "touch":

        def touch(index_file, command_args):
            index_file.touch()
        #enddef
        command = touch

    elif args.command == "clear":

        def clear(index_file, command_args):
            if index_file.load():
                index_file.save(Index())
        #enddef
        command = clear

    else:
        raise RuntimeError("Invalid command '{}'.".format(args.command))

    assert command is not None

    index_file = IndexFile(args.index)
    with index_file.lock():
        command(index_file, args.command_args)

#endif __main__
