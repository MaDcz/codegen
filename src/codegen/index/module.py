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

def type_to_parts(what, ns_seps=["."]):
    """Splits the input into parts. The input can be an iterable in which case it's expected
    that the individual items are strings or something covnertible to string. The result
    is a list of individual parts, before it is returned it's checked for validity."""
    type_parts = what
    if isinstance(what, str):
        splitted = False
        for sep in ns_seps:
            if what.find(sep) > -1:
                type_parts = what.split(sep)
                splitted = True
                break

        if not splitted:
            type_parts = [what]
    #endif

    try:
        iter(type_parts)
    except TypeError:
        raise TypeError("The input isn't iterable, expecting a sequence of type parts. Provided input is of type {}.".format(type(what)))

    for i in range(len(type_parts)):
        part = type_parts[i]
        if not isinstance(part, str):
            part = str(part)
            type_parts[i] = part
        if not part:
            raise ValueError("Discovered empty part in the input on index [{}].".format(i))
    #endfor

    return type_parts
#enddef

def validate_key(key, ns_seps=["."], res_sep="."):
    return res_sep.join(type_to_parts(key, ns_seps))
#enddef

from collections.abc import MutableMapping

class Index(MutableMapping):

    def __init__(self):
        self.__data = {}
        self.__ns_seps = ["."]
    #enddef

    def __getitem__(self, key):
        validated_key = validate_key(key, self.__ns_seps)
        return self.__data[validated_key]
    #enddef

    def __setitem__(self, key, value):
        validated_key = validate_key(key, self.__ns_seps)
        self.__data[validated_key] = value
    #enddef

    def __delitem__(self, key):
        validated_key = validate_key(key, self.__ns_seps)
        del self.__data[validated_key]
    #enddef

    def __iter__(self):
        # FIXME When iterating the types will appear in form of a dot notation. Check mapping view in abc if it could be of any help.
        return iter(self.__data)
    #enddef

    def __len__(self):
        return len(self.__data)
    #enddef

    def ensure(self, key, *path):
        validated_key = validate_key(key, self.__ns_seps)
        if validated_key not in self.__data:
            self.__data[validated_key] = {}
        d = self.__data[validated_key]
        for part in path:
            if part not in d:
                d[part] = {}
            d = d[part]
        return d
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

    def touch(self):
        try:
            with open(self.__filepath, "r"):
                import os
                os.utime(self.__filepath)
        except FileNotFoundError:
            self.save(Index())
    #enddef

#endclass
