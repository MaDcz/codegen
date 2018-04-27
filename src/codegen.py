#!/usr/bin/python


if __name__ == "__main__":

    import codemodel
    import sys

    class_diag = codemodel.from_json(sys.stdin.read())

#endif __main__
