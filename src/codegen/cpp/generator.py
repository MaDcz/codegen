import codegen.index
import codemodel

from contextlib import contextmanager
import copy
import logging
import sys

_version_major = 0
_version_minor = 1

# This is a workaround for 'nullcontext' missing in the 'contextlib' module. It was introduced
# only in Python version 3.7.
@contextmanager
def nullcontext():
    yield
#enddef

class Options(object):

    def __init__(self, args):
        self.args = args
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
    "uint" : "unsigned int", # '.iface' format specific
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
    "mad::codegen::tree::CompositeNode" : {
        "include" : "<mad/codegen/tree/compositenode.hpp>"
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
        logging.debug("IncludeTypesRegister.add() type='{}' printer='{}'".format(t, p))
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
                        # TODO Do some hierarchy for the class printers.
                if isinstance(printer, NamespacePrinter) \
                        or isinstance(printer, ClassPrinterAsComposite) \
                        or isinstance(printer, ClassPrinter):
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

            logging.debug("Resolved '{}' type in '{}' namespace to '{}'.".format(type_str, "::".join(context_ns), full_type_str))
            ret.add(full_type_str)
        #endfor

        return ret
    #enddef

    def debug(self):
        if self._register:
            logging.debug(">>>>>>>>>> Include types register content")
            for entry in self._register:
                logging.debug("type: {} printer: {}".format(entry["type"], str(entry["printer"])))
            logging.debug("<<<<<<<<<<")
    #enddef

#endclass

class Context(object):

    def __init__(self, options):
        self.__options = options
        self.__out = None
        self.__out_close = None
        self._printers_data = {}
        self.__phases_stack = []
        self.__namespaces_stack = []
        self.__used_types = IncludeTypesRegister()
        self.__index = None
        self.__index_lock = None
        self.__tempting_writes_buffer = []
    #enddef

    def __enter__(self):
        self.__prepare_index()

        return self
    #enddef

    def __exit__(self, exc_type, exc_value, traceback):
        # Persist changes in the index.
        self.__save_index()

        # Unlock the index.
  # FIXME Noticed that the index is written even on error and even if not changed (first codegen fails).
        if self.__index_lock is not None:
            self.__index_lock.__exit__(exc_type, exc_value, traceback)
            self.__index_lock = None

        self.__index == None

        self.__close_output()

        # TODO Errors handling etc.
    #enddef

    @property
    def options(self):
        return self.__options
    #enddef

    @property
    def out(self):
        if self.__out is None:
            self.__open_output()

        assert self.__out
        return self.__out
    #enddef

    def __open_output(self):
        self.__close_output()
        assert self.__out is None

        if self.in_phase(PHASE_HEADER_GEN):
            fp = self.options.header_output_filepath()
            if fp:
                logging.debug("Opening header file '{}' for output.".format(fp))
                self.__out, self.__out_close = (open(fp, "w"), lambda f: f.close())
        elif self.in_phase(PHASE_SOURCE_GEN):
            fp = self.options.source_output_filepath()
            if fp:
                logging.debug("Opening source file '{}' for output.".format(fp))
                self.__out, self.__out_close = (open(fp, "w"), lambda f: f.close())

        if self.__out is None:
            self.__out, self.__out_close = (sys.stdou, None)
    #enddef

    def __close_output(self):
        if self.__out is not None and self.__out_close is not None:
            self.__out_close(self.__out)
        self.__out = None
        self.__out_close = None
    #enddef

    @property
    def printers_data(self):
        return self._printers_data
    #enddef

    def begin_phase(self, phase):
        logging.debug(">>>>>>>>>> Phase {}.".format(phase))
        self.__phases_stack.append(phase)
    #enddef

    def end_phase(self, phase):
        logging.debug("<<<<<<<<<< Phase {}.".format(phase))
        assert self.__phases_stack
        popped_phase = self.__phases_stack.pop()
        assert popped_phase == phase
        if popped_phase == PHASE_HEADER_GEN or popped_phase == PHASE_SOURCE_GEN:
            self.__close_output()
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
        return self.__used_types
    #enddef

    def __prepare_index(self):
        assert self.__index is None

        # Try to load index file if specified through an option.
        if self.__options.args.index: # TODO Don't use args in options.
            try:
                index_file = codegen.index.IndexFile(self.__options.args.index)
                self.__index_lock = index_file.lock()
                self.__index_lock.__enter__()
                self.__index = index_file.load()
            except FileNotFoundError:
                pass

        # Start with empty index if we don't have an index file.
        if self.__index is None:
            self.__index = codegen.index.Index()

        # Debug.
        if self.__index:
            logging.debug(">>>>>>>>>> Index file '{}' content".format(self.__options.args.index))
            for key, value in self.__index.items():
                logging.debug("Found '{}' in index file '{}'".format(key, value))
                cpp_key = "::".join(key.split(".")) # TODO Do it in a better way after fixing the index iteration. cpp_types maybe can use tuples too after the fix.
                if cpp_key not in cpp_types:
                    cpp_types[cpp_key] = {"include": '"' + value["cpp"]["include"] + '"'} # TODO Careful with the access here.
                else:
                    assert key not in cpp_types
            logging.debug("<<<<<<<<<<")
        #endif
    #enddef

    @property
    def index(self):
        assert self.__index is not None
        return self.__index
    #enddef

    def __save_index(self):
        # TODO Work with index more nicely. Save it only if there are some changes.
        if self.__index is not None and self.__options.args.index:
            index_file = codegen.index.IndexFile(self.__options.args.index)
            index_file.save(self.__index)
    #enddef

    @contextmanager
    def tempting_writes_buffer_append(self, write):
        logging.debug("Appending tempting write {}.".format(len(self.__tempting_writes_buffer)))
        clear = bool(not self.__tempting_writes_buffer)
        self.__tempting_writes_buffer.append(write)
        yield
        if clear:
            self.clear_tempting_writes()
    #enddef

    def flush_tempting_writes(self):
        logging.debug("Flushing {} tempting writes.".format(len(self.__tempting_writes_buffer)))
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

    def __init__(self, context, parent_printer):
        self.__context = context
        self.__printers = []
        if parent_printer is not None:
            parent_printer.add_printer(self)
        self.__parent = parent_printer

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
            if logging.getLogger().level <= logging.DEBUG:
                debug_line = ""
                for arg in args:
                    debug_line += str(arg)
                logging.debug("writeln('{}'). (tempting={})".format(debug_line, mode & Printer.WRITE_FLAG_TEMPTING))

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

    def resolve_type(self, type_str_or_parts, scope=None):
        """Resolves the provided type in the scope of this printer."""

        def type_to_parts(what):
            """Splits the input into parts. The input can be an iterable in which case it's expected
            that the individual items are strings or something covnertible to string. Before the
            result is returned it's checked that it's valid."""
            type_parts = what
            if isinstance(what, str):
                if what.find(".") > -1:
                    type_parts = what.split(".")
                elif what.find("::") > -1:
                    type_parts = what.split("::")
                else:
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
                if not part and i > 0:
                    raise ValueError("Discovered empty part in the input on index [{}].".format(i))
            #endfor

            return type_parts
        #enddef

        type_parts = type_to_parts(type_str_or_parts)
        type_str = "::".join(type_parts)

        # Get the namespace in which the type was introduced.
        context_ns = []
        printer = scope if scope is not None else self
        while printer is not None:
            # TODO It would be safer to have deterministically specified if a printer introduces a namespace.
            if isinstance(printer, NamespacePrinter) \
                    or isinstance(printer, ClassPrinterAsComposite) \
                    or isinstance(printer, ClassPrinter):
                name = printer.node.attributes.get("name", "")
                if name:
                    context_ns.insert(0, name)
            printer = printer.parent
        #endwhile

        logging.debug("Resolving '{}' in namespace '{}'.".format(type_str, "::".join(context_ns)))

        full_type_parts = []
        for i in reversed(range(len(context_ns) + 1)):
            tmp = context_ns[0:i] + [type_str]
            tmp_str = "::".join(tmp)
            logging.debug("Resolving '{}', trying if '{}' is a known type.".format(type_str, tmp_str))
            if tmp_str in cpp_types:
                full_type_parts = tmp
                break
        #endfor

        if not full_type_parts:
            raise RuntimeError("Cannot resolve '{}' type in '{}' namespace.".format(type_str, "::".join(context_ns)))

        return tuple(full_type_parts)
    #enddef

#endclass

class NodePrinter(Printer):

    def __init__(self, node, context, parent_printer):
        super(NodePrinter, self).__init__(context, parent_printer)

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

class FileHeaderPrinter(Printer):

    def __init__(self, context, parent_printer):
        super(FileHeaderPrinter, self).__init__(context, parent_printer)
    #enddef

    def generate(self):

        def print_header(lines):
            width = max(len(ln) for ln in lines)
            self.writeln("// ", "=" * width)
            for ln in lines:
                self.writeln("// ", ln)
            self.writeln("// ", "=" * width)
        #enddef

        header_lines = []
        header_lines.append("Generated by codegen cpp generator ver. {}.{}.".format(_version_major, _version_minor))
        from datetime import datetime
        header_lines.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print_header(header_lines)

        if self.context.in_phase(PHASE_HEADER_GEN):
            self.writeln("#pragma once")
            self._generate_header_includes()
        elif self.context.in_phase(PHASE_SOURCE_GEN):
            self._generate_source_includes()
        return PRINTER_FINISHED
    #enddef

    def _generate_header_includes(self):
        self.context.used_types.debug()
        used_types = self.context.used_types.resolve()
        includes = set()
        for used_type in used_types:
            assert used_type in cpp_types
            include = cpp_types[used_type].get("include", "")
            if include:
                includes.add(include)

        for include in sorted(includes):
            assert include
            self.write("#include ")
            self.writeln(include)
    #enddef

    def _generate_source_includes(self):
        header_output_filename = self.context.options.header_output_filename()
        if header_output_filename:
            self.writeln('#include "' + self.context.options.header_output_filename()  + '"')
    #enddef

#endclass

class NamespacePrinter(NodePrinter):

    # XXX
    # This needs to generate namespace declaration (opening namespace).
    # Then all the namespace content needs to be written. At the end, namespace
    # needs to be closed.
    # XXX

    def __init__(self, node, context, parent_printer):
        super(NamespacePrinter, self).__init__(node, context, parent_printer)
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

class ClassPrinterAsComposite(NodePrinter):

    # XXX
    # Basic functionality: declare class, write content, end class.
    # Posibility ty forward declare the class and then implement it in .cpp file.

    # The visitor must got through the content multiple times. For example
    # attribute (const getter, non-const getter or optional setter,
    # and associated member) needs to genereate parts according to what
    # part we are generating.
    # XXX

    def __init__(self, node, context, parent_printer):
        super(ClassPrinterAsComposite, self).__init__(node, context, parent_printer)

        # Determine the base type. If base is provided explicitly, resolve it in the parent scope,
        # the base type can't be in the scope of this class.
        base_str = node.attributes.get("base", "")
        base_parts = []
        if base_str:
            base_parts = self.resolve_type(base_str, self.parent)
            base_str = "::".join(base_parts)
        else:
            base_parts = ["mad", "codegen", "tree", "CompositeNode"]
            base_str = "::".join(base_parts)

        self.__base_str = base_str

        # Add the base to the used types so an include will be generated.
        self.context.used_types.add(base_parts, self)

        # Register the printer between known types.
        full_name = []
        printer = self
        while printer is not None:
            if isinstance(printer, NamespacePrinter) \
                    or isinstance(printer, ClassPrinterAsComposite) \
                    or isinstance(printer, ClassPrinter):
                name = printer.node.attributes.get("name", "")
                if name:
                    full_name.insert(0, name)
            printer = printer.parent
        #endwhile

        full_name_str = "::".join(full_name)
        if full_name_str not in cpp_types:
            cpp_types[full_name_str] = {}
            logging.debug("Registered '{}' between known types.".format(full_name_str))
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
                    logging.debug("Switching section to public.")
                    tempting_section = self.writeln("public:",
                            mode=Printer.WRITE_MODE_TEMPTING,
                            after_write=set_section)
                elif section == SECTION_PROTECTED:
                    logging.debug("Switching section to protected.")
                    tempting_section = self.writeln("protected:",
                            mode=Printer.WRITE_MODE_TEMPTING,
                            after_write=set_section)
                elif section == SECTION_PRIVATE:
                    logging.debug("Switching section to private.")
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
            self.writeln("class {} : public {}".format(data.node_attrs.name, self.__base_str))
            self.writeln("{")

            # Constructor & destructor.
            with switch_section(SECTION_PUBLIC):
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
                    lambda p: isinstance(p, NamespacePrinter) or isinstance(p, ClassPrinterAsComposite)
            ns_or_class = self
            while ns_or_class:
                name = ns_or_class.node.attributes.get("name", "")
                assert name
                full_name.insert(0, name)
                ns_or_class = ns_or_class.find_parent(ns_or_class_cond)
            # FIXME Is the following okay? Also ns_or_class_cond is wrong.
            self.context.index[tuple(full_name)] = {"cpp": {"include": self.context.options.header_output_filepath()}}
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

                if written:
                    self.writeln()

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

class ClassPrinter(NodePrinter):

    # XXX
    # Basic functionality: declare class, write content, end class.
    # Posibility ty forward declare the class and then implement it in .cpp file.

    # The visitor must got through the content multiple times. For example
    # attribute (const getter, non-const getter or optional setter,
    # and associated member) needs to genereate parts according to what
    # part we are generating.
    # XXX

    def __init__(self, node, context, parent_printer):
        super(ClassPrinter, self).__init__(node, context, parent_printer)

        # Register the printer between known types.
        full_name = []
        printer = self
        while printer is not None:
            if isinstance(printer, NamespacePrinter) \
                    or isinstance(printer, ClassPrinterAsComposite) \
                    or isinstance(printer, ClassPrinter):
                name = printer.node.attributes.get("name", "")
                if name:
                    full_name.insert(0, name)
            printer = printer.parent
        #endwhile

        full_name_str = "::".join(full_name)
        if full_name_str not in cpp_types:
            cpp_types[full_name_str] = {}
            logging.debug("Registered '{}' between known types.".format(full_name_str))
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
                    logging.debug("Switching section to public.")
                    tempting_section = self.writeln("public:",
                            mode=Printer.WRITE_MODE_TEMPTING,
                            after_write=set_section)
                elif section == SECTION_PROTECTED:
                    logging.debug("Switching section to protected.")
                    tempting_section = self.writeln("protected:",
                            mode=Printer.WRITE_MODE_TEMPTING,
                            after_write=set_section)
                elif section == SECTION_PRIVATE:
                    logging.debug("Switching section to private.")
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
            # FIXME Is the following okay? Also ns_or_class_cond is wrong.
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

#TODO Improve types treatment:
# - reference_type - everything by reference
# - value_type non-fundamental type - store as value type, pass and return references
# - value_type fundamental type - everything by value

TREATMENT_VALUE_TYPE = "value_type"
TREATMENT_REFERENCE_TYPE = "reference_type"

class ClassMemberPrinter(NodePrinter):

    def __init__(self, node, context, parent_printer):
        super(ClassMemberPrinter, self).__init__(node, context, parent_printer)

        self._base_type = refine_cpp_type(node.attributes.get("type", []))
        self._base_type_is_fundamental = isinstance(self._base_type, str)
        self._full_type = self._base_type if self._base_type_is_fundamental else self.resolve_type(self._base_type)
        def determine_type_treatment():
            if self._base_type_is_fundamental:
                return TREATMENT_VALUE_TYPE
            else:
                full_type_str = "::".join(self._full_type)
                assert full_type_str in cpp_types
                return cpp_types[full_type_str].get("treatment", TREATMENT_REFERENCE_TYPE)
        #enddef
        self._type_treatment = determine_type_treatment()
        self._is_repeated = node.attributes.get("is_repeated", False)
    #enddef

#endclass

class ClassMemberPrinter_Property(ClassMemberPrinter):

    def __init__(self, node, context, parent_printer):
        super(ClassMemberPrinter_Property, self).__init__(node, context, parent_printer)

        if not self._base_type_is_fundamental:
            self.context.used_types.add(self._base_type, self)

        base_type_str = self._base_type if isinstance(self._base_type, str) else "::".join(self._base_type)
        if self._type_treatment == TREATMENT_VALUE_TYPE:
            if self._is_repeated:
                self.context.used_types.add([ "mad", "codegen", "ValuesListProperty" ], self)
                self._type_str = "mad::codegen::ValuesListProperty<{}>".format(base_type_str)
            else:
                self.context.used_types.add([ "mad", "codegen", "ValueProperty" ], self)
                self._type_str = "mad::codegen::ValueProperty<{}>".format(base_type_str)
        else:
            if self._is_repeated:
                self.context.used_types.add([ "mad", "codegen", "CompositesListProperty" ], self)
                self._type_str = "mad::codegen::CompositesListProperty<{}>".format(base_type_str)
            else:
                self.context.used_types.add([ "mad", "codegen", "CompositeProperty" ], self)
                self._type_str = "mad::codegen::CompositeProperty<{}>".format(base_type_str)
        #endif

        logging.debug("Class member '{}'. (type='{}' base_type='{}' treatment={} is_repeated={})"
                .format(self.node.attributes.get("name", ""), self._type_str, base_type_str,
                        self._type_treatment, self._is_repeated))
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

class ClassMemberPrinter_GetterSetter(ClassMemberPrinter):

    def __init__(self, node, context, parent_printer):
        super(ClassMemberPrinter_GetterSetter, self).__init__(node, context, parent_printer)

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
                    raise Exception("ClassMemberPrinter_GetterSetter used in unsupported phase ({})".format(self.context.current_phase))
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
                    raise Exception("ClassMemberPrinter_GetterSetter used in unsupported phase ({})".format(self.context.current_phase))
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
                    raise Exception("ClassMemberPrinter_GetterSetter used in unsupported phase ({})".format(self.context.current_phase))
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
                    raise Exception("ClassMemberPrinter_GetterSetter used in unsupported phase ({})".format(self.context.current_phase))
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
                    raise Exception("ClassMemberPrinter_GetterSetter used in unsupported phase ({})".format(self.context.current_phase))
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
                    raise Exception("ClassMemberPrinter_GetterSetter used in unsupported phase ({})".format(self.context.current_phase))
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
                    raise Exception("ClassMemberPrinter_GetterSetter used in unsupported phase ({})".format(self.context.current_phase))
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
                    raise Exception("ClassMemberPrinter_GetterSetter used in unsupported phase ({})".format(self.context.current_phase))
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
            super(Generator.RootPrinter, self).__init__(context, None)
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
            #endif

            return PRINTER_FINISHED
        #enddef

    #endclass

    def __init__(self):
        super(Generator, self).__init__()

        self.__context = None
        self.__printers_stack = []
    #enddef

    def run(self, node, args=None):
        with self.__ensure_context(args):
            logging.info("Processing class diagram, creating printers tree...")
            node.accept(self)
            logging.info("Printers tree created.")

            assert len(self.__printers_stack) == 1
            root_printer = self.__printers_stack.pop()
            assert isinstance(root_printer, Generator.RootPrinter)
            logging.info("Generating code...")
            root_printer.generate()
            logging.info("Code generation finished.")
    #enddef

    def visit_package(self, node):

        # Package doesn't have to have name, it can only serve the purpose of encapsulating
        # a bunch of nodes into a logical unit (as in the case of a top-level packages).
        if node.attributes.get("name", ""):
            self.__ensure_root_printer()

            assert self.__top_printer()
            printer = NamespacePrinter(node, self.__context, self.__top_printer())

            self.__printers_stack.append(printer)
            super(Generator, self).visit_package(node)
            self.__printers_stack.pop()
        else:
            def create_root_printer():
                root_printer = self.__create_root_printer()
                FileHeaderPrinter(self.__context, root_printer)
                return root_printer
            #enddef

            # Get into about types used in the class diagram.
            for cm_full_type, cm_info in node.attributes.get("using", {}).items():
                cpp_full_type = "::".join(cm_full_type.split("."))
                if cpp_full_type in cpp_types:
                    cpp_info = cpp_types[cpp_full_type]
                    if "treatment" in cm_info:
                        cpp_info["treatment"] = cm_info["treatment"]
            #endfor

            self.__ensure_root_printer(create_root_printer)
            super(Generator, self).visit_package(node)
    #enddef

    def visit_class(self, node):
        self.__ensure_root_printer()

        assert self.__top_printer()
        printer = ClassPrinterAsComposite(node, self.__context, self.__top_printer())

        self.__printers_stack.append(printer)
        super(Generator, self).visit_class(node)
        self.__printers_stack.pop()
    #enddef

    def visit_attribute(self, node):
        self.__ensure_root_printer()

        assert self.__top_printer()
        # FIXME This won't be always true. Parent printer probablu know what printer
        # to instanitate.
        printer = ClassMemberPrinter_Property(node, self.__context, self.__top_printer())

        self.__printers_stack.append(printer)
        super(Generator, self).visit_attribute(node)
        self.__printers_stack.pop()
    #enddef

    @contextmanager
    def __ensure_context(self, args):
        with Context(Options(args)) as context:
            self.__context = context
            yield
            self.__context = None
    #enddef

    def __ensure_root_printer(self, root_printer_create=None):
        if not self.__printers_stack:
            root_printer = root_printer_create() if root_printer_create is not None \
                    else self.__create_root_printer()
            self.__printers_stack.append(root_printer)
    #enddef

    def __create_root_printer(self):
        return Generator.RootPrinter(self.__context)
    #enddef

    def __top_printer(self):
        return self.__printers_stack[-1] if self.__printers_stack else None
    #enddef

#endclass
