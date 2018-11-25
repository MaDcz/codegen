import sys, copy
from contextlib import contextmanager

import codemodel

# This is a workaround for 'nullcontext' missing in the 'contextlib' module. It was introduced
# only in Python version 3.7.
@contextmanager
def nullcontext():
    yield
#enddef

class Output(object):
    pass
#enddef

def load_index_from_file(fpath):
    ret = {}

    with open(fpath, "r") as f:
        for ln in f:
            key_value = ln.rstrip().split(" ", maxsplit=1)
            if len(key_value) != 2:
                continue
            ret[key_value[0]] = key_value[1]

    return ret
#enddef

def save_index_to_file(index, fpath):
    with open(fpath, "w") as f:
        for key, value in index.items():
            print(key + " " + value, file=f)
#enddef

class Options(object):

    def __init__(self, args):
        self.args = args

        self._header_output_file = None
        self._source_output_file = None
    #enddef

    def header_output_filepath(self):
        return self.args.output_header + ".hpp" if self.args.output_header else ""
    #enddef

    def header_output_filename(self):
        filepath = self.header_output_filepath()
        if filepath:
            from os import path as pathutils
            return pathutils.basename(filepath)
        else:
            return filepath
    #enddef

    def header_output_file(self):
        if self._header_output_file is None:
            filepath = self.header_output_filepath()
            self._header_output_file = \
                open(filepath, "w") if filepath else sys.stdout

        assert self._header_output_file is not None
        return self._header_output_file
    #enddef

    def source_output_filepath(self):
        return self.args.output_source + ".cpp" if self.args.output_source else ""
    #enddef

    def source_output_filename(self):
        filepath = self.source_output_filepath()
        if filepath:
            from os import path as pathutils
            return pathutils.basename(filepath)
        else:
            return filepath
    #enddef

    def source_output_file(self):
        if self._source_output_file is None:
            filepath = self.source_output_filepath()
            self._source_output_file = \
                open(filepath, "w") if filepath else sys.stdout

        assert self._source_output_file is not None
        return self._source_output_file
    #enddef

#enddef

PHASE_NONE = -1

PHASE_HEADER_GEN = 0
PHASE_SOURCE_GEN = 1

PHASE_CLASS             = 10
PHASE_CLASS_DECL        = PHASE_CLASS + 1
PHASE_CLASS_IMPL        = PHASE_CLASS + 2
PHASE_CLASS_PIMPL_DECL  = PHASE_CLASS + 3
PHASE_CLASS_PIMPL_IMPL  = PHASE_CLASS + 4

PHASE_CLASS_MEMBER                    = 20
PHASE_CLASS_MEMBER_INIT               = PHASE_CLASS_MEMBER + 1
PHASE_CLASS_MEMBER_GETTER             = PHASE_CLASS_MEMBER + 2
PHASE_CLASS_MEMBER_CONST_GETTER       = PHASE_CLASS_MEMBER + 3
PHASE_CLASS_MEMBER_SETTER             = PHASE_CLASS_MEMBER + 4
PHASE_CLASS_MEMBER_PUBLIC_VARIABLE    = PHASE_CLASS_MEMBER + 5
PHASE_CLASS_MEMBER_PROTECTED_VARIABLE = PHASE_CLASS_MEMBER + 6
PHASE_CLASS_MEMBER_PRIVATE_VARIABLE   = PHASE_CLASS_MEMBER + 7

PRINTER_FINISHED = 1
PRINTER_NOT_FINISHED = 0

cpp_fundamental_types = {
    "bool" : "bool",
    "char" : "char",
    "signed char" : "char",
    "unsigned char" : "unsigned char",
    "wchar_t" : "wchar_t",
    "char16_t" : "char16_t",
    "char32_t" : "char32_t",
    "short" : "short int",
    "short int" : "short int",
    "signed short" : "short int",
    "signed short int" : "short int",
    "unsigned short" : "unsigned short int",
    "unsigned short int" : "unsigned short int",
    "int" : "int",
    "signed" : "int",
    "signed int" : "int",
    "unsigned" : "unsigned int",
    "unsigned int" : "unsigned int",
    "long" : "long int",
    "long int" : "long int",
    "signed long" : "long int",
    "signed long int" : "long int",
    "unsigned long" : "unsigned long int",
    "unsigned long int" : "unsigned long int",
    "long long" : "long long int",
    "long long int" : "long long int",
    "signed long long" : "long long int",
    "signed long long int" : "long long int",
    "unsigned long long" : "unsigned long long int",
    "unsigned long long int" : "unsigned long long int",
    "float" : "float",
    "double" : "double",
    "long double" : "long double"
}

cpp_types = {
    "mad::codegen::CompositeProperty" : {
        "include" : "<mad/codegen/compositeproperty.hpp>"
    },
    "mad::codegen::CompositesListProperty" : {
        "include" : "<mad/codegen/compositeslistproperty.hpp>"
    },
    "mad::codegen::ValueProperty" : {
        "include" : "<mad/codegen/valueproperty.hpp>"
    },
    "mad::codegen::ValuesListProperty" : {
        "include" : "<mad/codegen/valueslistproperty.hpp>"
    },
    "std::vector" : {
        "include" : "<vector>"
    }
}

def refine_cpp_type(cpp_type):
    is_fundamental = True
    refined_parts = []
    if len(cpp_type) == 1:
        for part in cpp_type[0].split(" "):
            if not part:
                continue

            if part not in cpp_fundamental_types:
                is_fundamental = False
                break

            if part == "signed" or part == "unsigned":
                refined_parts.insert(part, 0)
            else:
                refined_parts.append(part)
        #endfor
    else:
        is_fundamental = False
    #endif

    if is_fundamental:
        refined_type = cpp_fundamental_types.get(" ".join(refined_parts), "")
        if not refined_type:
            raise RuntimeError("Failed to refine C++ type ({})".format(cpp_type[0]))
        return refined_type
    else:
        return cpp_type
#enddef

class IncludeTypesRegister(object):

    def __init__(self):
        self._register = []
    #enddef

    def add(self, t, p=None):
        self._register.append({ "type": t, "printer": p })
    #enddef

    def resolve(self):
        ret = set()
        for entry in self._register:
            # Convert the type to string. Note that it could be relative.
            # TODO Add support for absolute types starting with '::'.
            type_str = "::".join(entry["type"])

            # Get the namespace in which the type was introduced.
            context_ns = []
            printer = entry["printer"]
            while printer is not None:
                if isinstance(printer, NamespacePrinter) or \
                        isinstance(printer, ClassPrinter):
                    name = printer.node.attributes.get("name", "")
                    if name:
                        context_ns.insert(0, name)
                printer = printer.parent
            #endwhile

            # Resolve the type, it has to be registered in advance.
            full_type_str = ""
            for i in reversed(range(len(context_ns) + 1)):
                tmp = "::".join(context_ns[0:i] + [ type_str ])
                if tmp in cpp_types:
                    full_type_str = tmp
                    break
            #endfor

            if not full_type_str:
                raise RuntimeError("Cannot resolve '{}' type in '{}' namespace.".format(type_str, "::".join(context_ns)))

            print("DBG Resolved '{}' type in '{}' namespace to '{}'.".format(type_str, "::".join(context_ns), full_type_str), file=sys.stderr)
            ret.add(full_type_str)
        #endfor

        return ret
    #enddef

    def debug(self):
        if self._register:
            print("DBG >>>>>>>>>> Include types register content", file=sys.stderr)
            for entry in self._register:
                print("DBG type: {} printer: {}".format(entry["type"], str(entry["printer"])), file=sys.stderr)
            print("DBG <<<<<<<<<<", file=sys.stderr)
    #enddef

#endclass

class Context(object):

    def __init__(self, options):
        self._options = options
        self._out = None
        self._printers_data = {}
        self.__phases_stack = []
        self.__namespaces_stack = []
        self._used_types = IncludeTypesRegister()
        self.__index = None
        self.__tempting_writes_buffer = []

        self._load_index()
    #enddef

    @property
    def options(self):
        return self._options
    #enddef

    @property
    def out(self):
        assert self._out is not None
        return self._out
    #enddef

    @property
    def printers_data(self):
        return self._printers_data
    #enddef

    def begin_phase(self, phase):
        print("DBG >>>>>>>>>> Phase {}".format(phase), file=sys.stderr)
        self.__phases_stack.append(phase)
        if phase == PHASE_HEADER_GEN:
            self._out = self._options.header_output_file()
        elif phase == PHASE_SOURCE_GEN:
            self._out = self._options.source_output_file()
    #enddef

    def end_phase(self, phase):
        print("DBG <<<<<<<<<< Phase {}".format(phase), file=sys.stderr)
        assert self.__phases_stack
        assert self.__phases_stack[-1] == phase
        self.__phases_stack.pop()
    #enddef

    @property
    def current_phase(self):
        return PHASE_NONE if not self.__phases_stack else self.__phases_stack[-1]
    #enddef

    def in_phase(self, phase):
        return phase in self.__phases_stack
    #enddef

    def begin_namespace(self, ns):
        self.__namespaces_stack.append(ns)
    #enddef

    def end_namespace(self, ns):
        assert self.__namespaces_stack
        assert self.__namespaces_stack[-1] == ns
        self.__namespaces_stack.pop()
    #enddef

    @property
    def open_namespaces(self):
        return list(self.__namespaces_stack)
    #enddef

    @property
    def used_types(self):
        return self._used_types
    #enddef

    def _load_index(self):
        assert self.__index is None

        # Try to load index file if specified through an option.
        if self._options.args.index: # TODO Don't use args in options.
            try:
                self.__index = load_index_from_file(self._options.args.index)
            except FileNotFoundError:
                pass

        # Start with empty index if we don't have an index file.
        if self.__index is None:
            self.__index = {}

        # Debug.
        if self.__index:
            print("DBG >>>>>>>>>> Index file '{}' content".format(self._options.args.index), file=sys.stderr)
            for key, value in self.__index.items():
                print("Found '{}' in index file '{}'".format(key, value), file=sys.stderr)
                if key not in cpp_types:
                    cpp_types[key] = { "include": '"' + value + '"' }
                else:
                    assert key not in cpp_types
            print("DBG <<<<<<<<<<", file=sys.stderr)
        #endif
    #enddef

    @property
    def index(self):
        assert self.__index is not None
        return self.__index
    #enddef

    def save_index(self):
        # TODO Work with index more nicely. Save it only if there are some changes.
        # TODO Locking while writing.
        if self.__index is not None and self._options.args.index:
            save_index_to_file(self.__index, self._options.args.index)
    #enddef

    @contextmanager
    def tempting_writes_buffer_append(self, write):
        print("DBG Appending tempting write {}.".format(len(self.__tempting_writes_buffer)), file=sys.stderr)
        clear = bool(not self.__tempting_writes_buffer)
        self.__tempting_writes_buffer.append(write)
        yield
        if clear:
            self.clear_tempting_writes()
    #enddef

    def flush_tempting_writes(self):
        print("DBG Flushing {} tempting writes.".format(len(self.__tempting_writes_buffer)), file=sys.stderr)
        tempting_writes_buffer = self.__tempting_writes_buffer
        self.__tempting_writes_buffer = []
        for write in tempting_writes_buffer:
            write()
    #enddef

    def clear_tempting_writes(self):
        del self.__tempting_writes_buffer[:]
    #enddef

#endclass

class Printer(object):

    WRITE_FLAG_TEMPTING = 1

    WRITE_MODE_DEFAULT = 0
    WRITE_MODE_TEMPTING = WRITE_MODE_DEFAULT | WRITE_FLAG_TEMPTING

    def __init__(self, context):
        self.__context = context
        self.__printers = []
        self.__parent = None

        assert(self.__context)
    #enddef

    @property
    def context(self):
        return self.__context
    #enddef

    # TODO Better encapsulate this.
    @property
    def printers(self):
        return list(self.__printers)
    #enddef

    def add_printer(self, printer):
        self.__printers.append(printer)
        printer.set_parent(self)
    #enddef

    def set_parent(self, printer):
        assert self.__parent is None
        self.__parent = printer
    #enddef

    @property
    def parent(self):
        return self.__parent
    #enddef

    def find_parent(self, cond):
        parent = self.parent
        while parent is not None:
            if cond(parent):
                break
            else:
                parent = parent.parent
        #endwhile

        return parent
    #enddef

    def __generate_key(self):
        self_type = type(self)
        return "{0}{1}{2}".format(self_type.__module__,
                "." if self_type.__module__ else "", self_type.__name__)
    #enddef

    def write(self, *args, mode=WRITE_MODE_DEFAULT, after_write=None):
        def write_args():
            for arg in args:
                self.__context.out.write(str(arg))

            if after_write:
                after_write()
        #enddef

        if mode & Printer.WRITE_FLAG_TEMPTING:
            return self.context.tempting_writes_buffer_append(write_args)
        else:
            self.context.flush_tempting_writes()
            write_args()
    #enddef

    def writeln(self, *args, mode=WRITE_MODE_DEFAULT, after_write=None):
        def write_args():
            # TODO If debug requested.
            debug_line = ""
            for arg in args:
                debug_line += str(arg)
            print("DBG writeln('{}'). (tempting={})".format(debug_line, mode & Printer.WRITE_FLAG_TEMPTING), file=sys.stderr)

            self.write(*args)
            print(file=self.__context.out)

            if after_write:
                after_write()
        #enddef

        if mode & Printer.WRITE_FLAG_TEMPTING:
            return self.context.tempting_writes_buffer_append(write_args)
        else:
            self.context.flush_tempting_writes()
            write_args()
    #enddef

#endclass

class NodePrinter(Printer):

    def __init__(self, context, node):
        super(NodePrinter, self).__init__(context)

        self.__node = node

        assert(self.__node)
    #enddef

    @property
    def node(self):
        return self.__node
    #enddef

    def get_node_attribute(self, attr_path, default=None):
        attr_path_parts = attr_path.split(".")
        attrs_view = self.__node.attributes
        for part in attr_path_parts[:-1]:
            attrs_view = attrs_view.get(part, {})
        return attrs.get(attr_path_parts[-1], default)
    #enddef

#endclass

class IncludesPrinter(Printer):

    def __init__(self, context):
        super(IncludesPrinter, self).__init__(context)
    #enddef

    def generate(self):
        if self.context.in_phase(PHASE_HEADER_GEN):
            self._generate_header_includes()
        elif self.context.in_phase(PHASE_SOURCE_GEN):
            self._generate_source_includes()
        return PRINTER_FINISHED
    #enddef

    def _generate_header_includes(self):
        self.context.used_types.debug()
        used_types = self.context.used_types.resolve()
        for used_type in used_types:
            assert used_type in cpp_types
            include = cpp_types[used_type].get("include", "")
            if include:
                self.write("#include ")
                self.writeln(include)
    #enddef

    def _generate_source_includes(self):
        self.writeln("#include \"" + self.context.options.header_output_filename() + "\"")
    #enddef

#endclass

class NamespacePrinter(NodePrinter):

    # XXX
    # This needs to generate namespace declaration (opening namespace).
    # Then all the namespace content needs to be written. At the end, namespace
    # needs to be closed.
    # XXX

    def __init__(self, context, node):
        super(NamespacePrinter, self).__init__(context, node)
    #enddef

    def generate(self):
        finished_flag = PRINTER_FINISHED

        # TODO Do a special node for the root node.
        name = self.node.attributes.get("name", "")
        if name:
            self.writeln("namespace ", name, " {")
            self.context.begin_namespace(self.node)

        # TODO Move this to the base where printers property will be better encapsulated.
        for printer in self.printers:
            finished_flag &= printer.generate()

        if name:
            self.writeln("} // namespace ", "::".join(ns.attributes["name"] for ns in self.context.open_namespaces))
            self.context.end_namespace(self.node)

        return finished_flag
    #enddef

#endclass

class ClassPrinter(NodePrinter):

    # XXX
    # Basic functionality: declare class, write content, end class.
    # Posibility ty forward declare the class and then implement it in .cpp file.

    # The visitor must got through the content multiple times. For example
    # attribute (const getter, non-const getter or optional setter,
    # and associated member) needs to genereate parts according to what
    # part we are generating.
    # XXX

    def __init__(self, context, node):
        super(ClassPrinter, self).__init__(context, node)
    #enddef

    def set_parent(self, printer):
        super(ClassPrinter, self).set_parent(printer)

        # Register the printer between known types.
        full_name = []
        printer = self
        while printer is not None:
            if isinstance(printer, NamespacePrinter) or \
                    isinstance(printer, ClassPrinter):
                name = printer.node.attributes.get("name", "")
                if name:
                    full_name.insert(0, name)
            printer = printer.parent
        #endwhile

        full_name_str = "::".join(full_name)
        if full_name_str not in cpp_types:
            cpp_types[full_name_str] = {}
            print("DBG Registered '{}' between known types.".format(full_name_str), file=sys.stderr)
        else:
            raise RuntimeError("Redefinition of type '{}'.".format(full_name_str))
    #enddef

    def generate(self):

        SECTION_NONE = 0
        SECTION_PUBLIC = 1
        SECTION_PROTECTED = 2
        SECTION_PRIVATE = 3

        class data:
            finished_flag = PRINTER_FINISHED
            section = SECTION_NONE

            class node_attrs:
                name = self.node.attributes.get("name", "")
                is_struct = self.node.attributes.get("is_struct", False)

                class cpp:
                    pimpl = self.node.attributes.get("cpp", {}).get("pimpl", False)
                #endclass
            #endclass
        #endclass

        if not data.node_attrs.name:
            raise RuntimeError("Missing or empty 'name' attribute of a 'class' node")

        for printer in self.printers:
            data.node_attrs.cpp.pimpl |= printer.node.attributes.get("cpp", {}).get("pimpl", False)

        def switch_section(section):
            tempting_section = nullcontext()

            if data.section == section:
                pass
            elif section == SECTION_NONE:
                data.section = SECTION_NONE
            elif section in [SECTION_PUBLIC, SECTION_PROTECTED, SECTION_PRIVATE]:
                # Note that the section variable has to be updated only after the write actually
                # happens, otherwise it would be misleading.
                def set_section():
                    data.seciton = section
                #enddef

                if section == SECTION_PUBLIC:
                    print("DBG Switching section to public.", file=sys.stderr)
                    tempting_section = self.writeln("public:",
                            mode=Printer.WRITE_MODE_TEMPTING,
                            after_write=set_section)
                elif section == SECTION_PROTECTED:
                    print("DBG Switching section to protected.", file=sys.stderr)
                    tempting_section = self.writeln("protected:",
                            mode=Printer.WRITE_MODE_TEMPTING,
                            after_write=set_section)
                elif section == SECTION_PRIVATE:
                    print("DBG Switching section to private.", file=sys.stderr)
                    tempting_section = self.writeln("private:",
                            mode=Printer.WRITE_MODE_TEMPTING,
                            after_write=set_section)
            else:
                raise Exception("Invalid section ({}), need one of SECTION_NONE, SECTION_PUBLIC, SECTION_PROTECTED or SECTION_PRIVATE.".format(section))

            return tempting_section
        #enddef

        def generate_content(phases):
            for phase in phases:
                self.context.begin_phase(phase)

                tempting_section = nullcontext()

                if self.context.in_phase(PHASE_CLASS_DECL) or self.context.in_phase(PHASE_CLASS_PIMPL_DECL):
                    if phase == PHASE_CLASS_MEMBER_PUBLIC_VARIABLE:
                        tempting_section = switch_section(SECTION_PUBLIC)
                    elif phase == PHASE_CLASS_MEMBER_PROTECTED_VARIABLE:
                        tempting_section = switch_section(SECTION_PROTECTED)
                    elif phase == PHASE_CLASS_MEMBER_PRIVATE_VARIABLE:
                        tempting_section = switch_section(SECTION_PRIVATE)
                #endif

                with tempting_section:
                    for printer in self.printers:
                            # FIXME This isn't sufficient, members will indicate that they didn't
                            # finished in the very beginning and it will be carried over through
                            # the whole process in the return value.
                            data.finished_flag &= printer.generate()
                #endwith

                self.context.end_phase(phase)
        #enddef

        # TODO Structs isn't supported properly, generated as classes at the moment.

        if self.context.in_phase(PHASE_HEADER_GEN):

            # Start class/struct.
            self.context.begin_phase(PHASE_CLASS_DECL)
            self.writeln("struct " if data.node_attrs.is_struct else "class ", data.node_attrs.name)
            self.writeln("{")

            # Constructor & destructor.
            with switch_section(SECTION_PUBLIC):
                if data.node_attrs.cpp.pimpl:
                    self.writeln("  {}();".format(data.node_attrs.name))
                self.writeln("  virtual ~{}();".format(data.node_attrs.name))

            # Generate methods.
            generate_content([ PHASE_CLASS_MEMBER_GETTER,
                               PHASE_CLASS_MEMBER_CONST_GETTER,
                               PHASE_CLASS_MEMBER_SETTER ])

            # Put member variables in a seperate public/protected/private sections.
            with switch_section(SECTION_NONE):
                pass

            # Generate member variables.
            generate_content([ PHASE_CLASS_MEMBER_PUBLIC_VARIABLE,
                               PHASE_CLASS_MEMBER_PROTECTED_VARIABLE,
                               PHASE_CLASS_MEMBER_PRIVATE_VARIABLE ])

            # Add private implementation member if needed.
            if data.node_attrs.cpp.pimpl:
                with switch_section(SECTION_PRIVATE):
                    self.writeln("  class Impl;")
                    self.writeln("  Impl* m_impl = nullptr;")

            self.writeln("};")
            self.context.end_phase(PHASE_CLASS_DECL)
            data.finished_flag = PRINTER_NOT_FINISHED

            full_name = []
            ns_or_class_cond = \
                    lambda p: isinstance(p, NamespacePrinter) or isinstance(p, ClassPrinter)
            ns_or_class = self
            while ns_or_class:
                name = ns_or_class.node.attributes.get("name", "")
                assert name
                full_name.insert(0, name)
                ns_or_class = ns_or_class.find_parent(ns_or_class_cond)
            self.context.index["::".join(full_name)] = self.context.options.header_output_filepath()
        #endif

        # Reset section before source generation starts.
        with switch_section(SECTION_NONE):
            pass

        if self.context.in_phase(PHASE_SOURCE_GEN):
            if data.node_attrs.cpp.pimpl:
                # Declare pimpl class.
                self.context.begin_phase(PHASE_CLASS_PIMPL_DECL)
                self.writeln("class ", data.node_attrs.name, "::Impl")
                self.writeln("{")

                generate_content([ PHASE_CLASS_MEMBER_GETTER,
                                   PHASE_CLASS_MEMBER_CONST_GETTER,
                                   PHASE_CLASS_MEMBER_SETTER ])

                with switch_section(SECTION_NONE):
                    pass

                generate_content([ PHASE_CLASS_MEMBER_PUBLIC_VARIABLE,
                                   PHASE_CLASS_MEMBER_PROTECTED_VARIABLE,
                                   PHASE_CLASS_MEMBER_PRIVATE_VARIABLE ])

                self.writeln("};")
                self.context.end_phase(PHASE_CLASS_PIMPL_DECL)

                # Implement pimpl class methods.
                self.context.begin_phase(PHASE_CLASS_PIMPL_IMPL)

                generate_content([ PHASE_CLASS_MEMBER_GETTER,
                                   PHASE_CLASS_MEMBER_CONST_GETTER,
                                   PHASE_CLASS_MEMBER_SETTER ])

                self.context.end_phase(PHASE_CLASS_PIMPL_IMPL)
            #endif

            self.context.begin_phase(PHASE_CLASS_IMPL)

            # Constructor & destructor.
            if data.node_attrs.cpp.pimpl:
                self.writeln("{name}::{name}()".format(name=data.node_attrs.name))

                self.context.begin_phase(PHASE_CLASS_MEMBER_INIT)
                written = False
                def set_written():
                    nonlocal written
                    written = True
                #enddef
                with self.write("  : ", mode=Printer.WRITE_MODE_TEMPTING, after_write=set_written):
                    for printer in self.printers:
                        with self.write(",\n    ", mode=Printer.WRITE_MODE_TEMPTING) if written else nullcontext():
                            # TODO Update finished flag.
                            printer.generate()
                    with self.write(",\n    ", mode=Printer.WRITE_MODE_TEMPTING) if written else nullcontext():
                        self.writeln("m_impl(new Impl)")
                #endwith
                self.context.end_phase(PHASE_CLASS_MEMBER_INIT)

                self.writeln("{")
                self.writeln("}")
                self.writeln("{name}::~{name}()".format(name=data.node_attrs.name))
                self.writeln("{")
                self.writeln("  delete m_impl;")
                self.writeln("  m_impl = nullptr;")
                self.writeln("}")
            else:
                self.writeln("{name}::{name}()".format(name=data.node_attrs.name))

                self.context.begin_phase(PHASE_CLASS_MEMBER_INIT)
                written = False
                def set_written():
                    nonlocal written
                    written = True
                #enddef
                with self.write("  : ", mode=Printer.WRITE_MODE_TEMPTING, after_write=set_written):
                    for printer in self.printers:
                        with self.write(",\n    ", mode=Printer.WRITE_MODE_TEMPTING) if written else nullcontext():
                            # TODO Update finished flag.
                            printer.generate()
                #endwith
                self.context.end_phase(PHASE_CLASS_MEMBER_INIT)

                self.writeln("{")
                self.writeln("}")
                self.writeln("{name}::~{name}()".format(name=data.node_attrs.name))
                self.writeln("{")
                self.writeln("}")
            #endif

            generate_content([ PHASE_CLASS_MEMBER_GETTER,
                               PHASE_CLASS_MEMBER_CONST_GETTER,
                               PHASE_CLASS_MEMBER_SETTER ])

            self.context.end_phase(PHASE_CLASS_IMPL)

        return data.finished_flag
    #enddef

#endclass

# TODO Modify this to fit its name and use it instead of the former implementation.
class ClassMemberPrinterAsProperty(NodePrinter):

    def __init__(self, context, node):
        super(ClassMemberPrinterAsProperty, self).__init__(context, node)

        self._base_type = refine_cpp_type(node.attributes.get("type", []))
        self._is_repeated = node.attributes.get("is_repeated", False)
        base_type_is_fundamental = isinstance(self._base_type, str) # TODO Test the string properly for Python 2 and 3
        base_type_str = self._base_type if base_type_is_fundamental else "::".join(self._base_type)
        self._type_is_fundamental = not self._is_repeated and base_type_is_fundamental
        if self._type_is_fundamental:
            if self._is_repeated:
                self.context.used_types.add([ "mad", "codegen", "ValuesListProperty" ], self)
                self._type_str = "mad::codegen::ValuesListProperty<{}>".format(base_type_str)
            else:
                self.context.used_types.add([ "mad", "codegen", "ValueProperty" ], self)
                self._type_str = "mad::codegen::ValueProperty<{}>".format(base_type_str)
        else:
            self.context.used_types.add(self._base_type, self)
            if self._is_repeated:
                self.context.used_types.add([ "mad", "codegen", "CompositesListProperty" ], self)
                self._type_str = "mad::codegen::CompositesListProperty<{}>".format(base_type_str)
            else:
                self.context.used_types.add([ "mad", "codegen", "CompositeProperty" ], self)
                self._type_str = "mad::codegen::CompositeProperty<{}>".format(base_type_str)
        #endif
        self._default_value = "" if not self._type_is_fundamental else "false" if self._type_str == "bool" else "0"
    #enddef

    def generate(self):
        finished_flag = PRINTER_FINISHED

        def generate_class_decl():
            if self.context.in_phase(PHASE_CLASS_MEMBER_PUBLIC_VARIABLE):
                # TODO Initialization (default value).
                self.writeln("  {} {};".format(self._type_str, self.node.attributes.get("name", "")))
        #enddef

        def generate_class_impl():
            if self.context.in_phase(PHASE_CLASS_MEMBER_INIT):
                self.write('{0}(*this, "{0}")'.format(self.node.attributes.get("name", "")))
        #enddef

        if self.context.in_phase(PHASE_CLASS_DECL):
            generate_class_decl()
        elif self.context.in_phase(PHASE_CLASS_IMPL):
            generate_class_impl()

        return finished_flag
    #enddef

#endclass

class ClassMemberPrinter(NodePrinter):

    def __init__(self, context, node):
        super(ClassMemberPrinter, self).__init__(context, node)

        self._base_type = refine_cpp_type(node.attributes.get("type", []))
        self._is_repeated = node.attributes.get("is_repeated", False)
        base_type_is_fundamental = isinstance(self._base_type, str) # TODO Test the string properly for Python 2 and 3
        base_type_str = self._base_type if base_type_is_fundamental else "::".join(self._base_type)
        self._type_is_fundamental = not self._is_repeated and base_type_is_fundamental
        self._type_str = "std::vector<{}>".format(base_type_str) if self._is_repeated else base_type_str
        self._default_value = "" if not self._type_is_fundamental else "false" if self._type_str == "bool" else "0"

        if not base_type_is_fundamental:
            self.context.used_types.add(self._base_type, self)
        if self._is_repeated:
            self.context.used_types.add([ "std", "vector" ])
    #enddef

    def generate(self):
        finished_flag = PRINTER_FINISHED

        pimpl = self.node.attributes.get("cpp", {}).get("pimpl", None)
        if pimpl is None:
            pimpl = self.parent.node.attributes.get("cpp", {}).get("pimpl", False)

        def generate_class_decl():
            if self._type_is_fundamental:
                if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                    pass
                elif self.context.current_phase == PHASE_CLASS_MEMBER_CONST_GETTER:
                    # TODO Use format() in a better way (arguments could be preparend in advance).
                    # TODO Use ''' style string.
                    self.writeln("  {} {}() const;".format(self._type_str, self.node.attributes.get("name", "")))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    # TODO Also consider R-value for move semantic.
                    self.writeln("  void {}({} value);".format(self.node.attributes.get("name", ""), self._type_str))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_PRIVATE_VARIABLE:
                    if not pimpl:
                        # TODO Initialization (default value).
                        self.write("  {} m_{}".format(self._type_str, self.node.attributes.get("name", "")))
                        if self._default_value:
                            self.write(" = {}".format(self._default_value))
                        self.writeln(";")
                else:
                    raise Exception("ClassMemberPrinter used in unsupported phase ({})".format(self.context.current_phase))
            else:
                if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                    # TODO Use format() in a better way (arguments could be preparend in advance).
                    # TODO Use ''' style string.
                    self.writeln("  {}& {}();".format(self._type_str, self.node.attributes.get("name", "")))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_CONST_GETTER:
                    self.writeln("  const {}& {}() const;".format(self._type_str, self.node.attributes.get("name", "")))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    # TODO Also consider R-value for move semantic.
                    self.writeln("  void {}({} value);".format(self.node.attributes.get("name", ""), self._type_str))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_PRIVATE_VARIABLE:
                    if not pimpl:
                        # TODO Initialization (default value).
                        self.writeln("  {} m_{};".format(self._type_str, self.node.attributes.get("name", "")))
                else:
                    raise Exception("ClassMemberPrinter used in unsupported phase ({})".format(self.context.current_phase))
        #enddef

        def generate_class_impl():
            if self._type_is_fundamental:
                if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                    pass
                elif self.context.current_phase == PHASE_CLASS_MEMBER_CONST_GETTER:
                    # TODO Distinguish between types ('value' vs. 'reference' type).
                    # TODO Use format() in a better way (arguments could be preparend in advance).
                    # TODO Use ''' style string.
                    self.writeln("{} {}::{}() const".format(self._type_str, self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", "")))
                    self.writeln("{")
                    if not pimpl:
                        self.writeln("  return m_{};".format(self.node.attributes.get("name", "")))
                    else:
                        self.writeln("  return m_impl->{}();".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    # TODO Also consider R-value for move semantic.
                    self.writeln("void {}::{}({} value)".format(self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", ""), self._type_str))
                    self.writeln("{")
                    if not pimpl:
                        self.writeln("  m_{} = value;".format(self.node.attributes.get("name", "")))
                    else:
                        self.writeln("  m_impl->{}(value);".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                else:
                    raise Exception("ClassMemberPrinter used in unsupported phase ({})".format(self.context.current_phase))
            else:
                if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                    # TODO Distinguish between types ('value' vs. 'reference' type).
                    # TODO Use format() in a better way (arguments could be preparend in advance).
                    # TODO Use ''' style string.
                    self.writeln("{}& {}::{}()".format(self._type_str, self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", "")))
                    self.writeln("{")
                    if not pimpl:
                        self.writeln("  return m_{};".format(self.node.attributes.get("name", "")))
                    else:
                        self.writeln("  return m_impl->{}();".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                elif self.context.current_phase == PHASE_CLASS_MEMBER_CONST_GETTER:
                    self.writeln("const {}& {}::{}() const".format(self._type_str, self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", "")))
                    self.writeln("{")
                    if not pimpl:
                        self.writeln("  return m_{};".format(self.node.attributes.get("name", "")))
                    else:
                        self.writeln("  return m_impl->{}();".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    # TODO Also consider R-value for move semantic.
                    self.writeln("void {}::{}({} value)".format(self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", ""), self._type_str))
                    self.writeln("{")
                    if not pimpl:
                        self.writeln("  m_{} = std::move(value);".format(self.node.attributes.get("name", "")))
                    else:
                        self.writeln("  m_impl->{}(std::move(value));".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                else:
                    raise Exception("ClassMemberPrinter used in unsupported phase ({})".format(self.context.current_phase))
        #enddef

        def generate_pimpl_decl():
            if not pimpl:
                return

            if self._type_is_fundamental:
                if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                    pass
                elif self.context.current_phase == PHASE_CLASS_MEMBER_CONST_GETTER:
                    self.writeln("  {} {}() const;".format(self._type_str, self.node.attributes.get("name", "")))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    self.writeln("  void {}({} value);".format(self.node.attributes.get("name", ""), self._type_str))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_PRIVATE_VARIABLE:
                    self.write("  {} m_{}".format(self._type_str, self.node.attributes.get("name", "")))
                    if self._default_value:
                        self.write(" = {}".format(self._default_value))
                    self.writeln(";")
                else:
                    raise Exception("ClassMemberPrinter used in unsupported phase ({})".format(self.context.current_phase))
            else:
                if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                    self.writeln("  {}& {}();".format(self._type_str, self.node.attributes.get("name", "")))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_CONST_GETTER:
                    pass
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    self.writeln("  void {}({} value);".format(self.node.attributes.get("name", ""), self._type_str))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_PRIVATE_VARIABLE:
                    self.writeln("  {} m_{};".format(self._type_str, self.node.attributes.get("name", "")))
                else:
                    raise Exception("ClassMemberPrinter used in unsupported phase ({})".format(self.context.current_phase))
        #enddef

        def generate_pimpl_impl():
            if not pimpl:
                return

            if self._type_is_fundamental:
                if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                    pass
                elif self.context.current_phase == PHASE_CLASS_MEMBER_CONST_GETTER:
                    self.writeln("{} {}::Impl::{}() const".format(self._type_str, self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", "")))
                    self.writeln("{")
                    self.writeln("  return m_{};".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    self.writeln("void {}::Impl::{}({} value)".format(self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", ""), self._type_str))
                    self.writeln("{")
                    self.writeln("  m_{} = value;".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                else:
                    raise Exception("ClassMemberPrinter used in unsupported phase ({})".format(self.context.current_phase))
            else:
                if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                    self.writeln("{}& {}::Impl::{}()".format(self._type_str, self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", "")))
                    self.writeln("{")
                    self.writeln("  return m_{};".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                elif self.context.current_phase == PHASE_CLASS_MEMBER_CONST_GETTER:
                    pass
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    self.writeln("void {}::Impl::{}({} value)".format(self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", ""), self._type_str))
                    self.writeln("{")
                    self.writeln("  m_{} = std::move(value);".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                else:
                    raise Exception("ClassMemberPrinter used in unsupported phase ({})".format(self.context.current_phase))
        #enddef

        if self.context.in_phase(PHASE_CLASS_DECL):
            generate_class_decl()
        elif self.context.in_phase(PHASE_CLASS_IMPL):
            generate_class_impl()
        elif self.context.in_phase(PHASE_CLASS_PIMPL_DECL):
            generate_pimpl_decl()
        elif self.context.in_phase(PHASE_CLASS_PIMPL_IMPL):
            generate_pimpl_impl()

        return finished_flag
    #enddef

#endclass

class Generator(codemodel.ClassDiagramVisitor):

    class RootPrinter(Printer):

        def __init__(self, context):
            super(Generator.RootPrinter, self).__init__(context)
        #enddef

        def generate(self):
            if self.printers:
                for phase in [ PHASE_HEADER_GEN, PHASE_SOURCE_GEN ]:

                    finished_flag = PRINTER_FINISHED

                    self.context.begin_phase(phase)

                    for printer in self.printers:
                        finished_flag &= printer.generate()

                    self.context.end_phase(phase)

                    if finished_flag == PRINTER_FINISHED:
                        break
                #endfor

                self.context.save_index()
            #endif

            return PRINTER_FINISHED
        #enddef

    #endclass

    class DiagramNodeGuard(object):

        def __init__(self, printers_stack, root_printer_create):
            assert printers_stack is not None
            assert root_printer_create

            self._printers_stack = printers_stack
            self._root_printer_create = root_printer_create
        #enddef

        def __enter__(self):
            if not self._printers_stack:
                self._printers_stack.append(self._root_printer_create())
        #enddef

        def __exit__(self, exc_type, exc_value, traceback):
            assert len(self._printers_stack) > 0
        #enddef

    #endclass

    def __init__(self, args=None):
        super(Generator, self).__init__()

        self._context = Context(Options(args))
        self._printers_stack = []
    #enddef

    def run(self, node):
        node.accept(self)

        if len(self._printers_stack) == 1:
            root_printer = self._printers_stack.pop()
            assert isinstance(root_printer, Generator.RootPrinter)
            root_printer.generate()
    #enddef

    def visit_package(self, node):
        def create_root_printer():
            root_printer = self._create_root_printer()
            root_printer.add_printer(IncludesPrinter(self._context))
            return root_printer
        #enddef

        if node.attributes.get("name", ""): # TODO Distinguish somehow the package node in the parser.
            with self._create_node_scope(create_root_printer):
                top_printer = self._top_printer()
                assert top_printer

                printer = NamespacePrinter(self._context, node)
                top_printer.add_printer(printer)

                self._printers_stack.append(printer)
                super(Generator, self).visit_package(node)
                self._printers_stack.pop()
        else:
            super(Generator, self).visit_package(node)
    #enddef

    def visit_class(self, node):
        with self._create_node_scope():
            top_printer = self._top_printer()
            assert top_printer

            printer = ClassPrinter(self._context, node)
            top_printer.add_printer(printer)

            self._printers_stack.append(printer)
            super(Generator, self).visit_class(node)
            self._printers_stack.pop()
    #enddef

# TODO
#    def visit_operation(self, node):
#        name = node.attributes.get("name", "")
#        return_type = node.attributes.get("return_type", "void")
#        params = node.attributes.get("params", [])
#        is_static = node.attributes.get("is_static", False)
#
#        if not name:
#            raise RuntimeError("Missing or empty 'name' attribute of a 'operation' node")
#
#        self.writeln("static " if is_static else "", return_type, " ", name,
#            "(", ", ".join(params), ");")
#        super(Generator, self).visit_operation(node)
#    #enddef

    def visit_attribute(self, node):
        with self._create_node_scope():
            top_printer = self._top_printer()
            assert top_printer

            # FIXME This won't be always true. Parent printer probablu know what printer
            # to instanitate.
            printer = ClassMemberPrinterAsProperty(self._context, node)
            top_printer.add_printer(printer)

            self._printers_stack.append(printer)
            super(Generator, self).visit_attribute(node)
            self._printers_stack.pop()
    #enddef

    def _create_node_scope(self, root_printer_create=None):
        return Generator.DiagramNodeGuard(self._printers_stack,
                root_printer_create if root_printer_create is not None else self._create_root_printer)
    #enddef

    def _create_root_printer(self):
        return Generator.RootPrinter(self._context)
    #enddef

    def _top_printer(self):
        return self._printers_stack[-1] if self._printers_stack else None
    #enddef

#endclass
