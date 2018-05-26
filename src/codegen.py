#!/usr/bin/python

if __name__ == "__main__":
    import codegen
    import codemodel
    import sys

    raw_data = sys.stdin.read()
    #print(raw_data) TODO Add debugging option.
    class_diag = codemodel.from_json(raw_data)
    gen = codegen.cpp.Generator()
    class_diag.accept(gen)
#endif __main__
