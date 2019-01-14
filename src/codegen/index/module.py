import logging

class LockFile(object):

    def __init__(self, filepath, ):
        self.__filepath = filepath
        self.__file = None
    #enddef

    def __enter__(self):
        import time

        while self.__file is None:
            try:
                self.__file = open(self.__filepath, "x")
                logging.debug("Created lock file '{}'".format(self.__filepath))
            except Exception as e:
                time.sleep(.2)

        return self
    #enddef

    def __exit__(self, exc_type, exc_value, traceback):
        if self.__file is not None:
            self.__file.close()
            self.__file = None
            import os
            os.remove(self.__filepath)
            logging.debug("Removed lock file '{}'".format(self.__filepath))
    #enddef

#endclass

from collections.abc import MutableMapping

class Index(MutableMapping):

    def __init__(self):
        self.__data = {}
    #enddef

    def __getitem__(self, key):
        if isinstance(key, str):
            key = (key, ) # TODO Run it through the parser to recognize namespaces.
        elif not isinstance(key, tuple):
            raise Exception("The 'key' has to be a full type in form of str or already dissected to a tuple.")

        return self.__data[".".join(key)]
    #enddef

    def __setitem__(self, key, value):
        if isinstance(key, str):
            key = (key, ) # TODO Run it through the parser to recognize namespaces.
        elif not isinstance(key, tuple):
            raise Exception("The 'key' has to be a full type in form of str or already dissected to a tuple.")

        self.__data[".".join(key)] = value
    #enddef

    def __delitem__(self, key):
        del self.__data[".".join(key)]
    #enddef

    def __iter__(self):
        # FIXME When iterating the types will appear in form of a dot notation. Check mapping view in abc if it could be of any help.
        return iter(self.__data)
    #enddef

    def __len__(self):
        return len(self.__data)
    #enddef

    def load_json(self, f):
        import json
        self.__data = json.load(f)
    #enddef

    def dump_json(self, f):
        import json
        json.dump(self.__data, f)
    #enddef

#endclass

class IndexFile(object):

    def __init__(self, filepath):
        super(IndexFile, self).__init__()

        self.__filepath = filepath
    #enddef

    def lock(self):
        return LockFile(self.__filepath + ".lock")
    #enddef

    def load(self):
        index = Index()

        try:
            with open(self.__filepath) as index_file:
                index.load_json(index_file)
        except FileNotFoundError:
            pass

        return index
    #enddef

    def save(self, index):
        with open(self.__filepath, "w") as index_file:
            index.dump_json(index_file)
    #enddef

#endclass
