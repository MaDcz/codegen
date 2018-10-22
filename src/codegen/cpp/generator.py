import sys, copy
import codemodel

class Output(object):
    pass
#enddef

class Options(object):

    def __init__(self, args):
        self.args = args

        self._header_output_file = None
        self._source_output_file = None
    #enddef

    def header_output_filepath(self):
        return self.args.output + ".hpp" if self.args.output else ""
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
        if self.args.output:
            if self._header_output_file is None:
                self._header_output_file = \
                        open(self.header_output_filepath(), "w")
            return self._header_output_file
        else:
            return sys.stdout
    #enddef

    def source_output_filepath(self):
        return self.args.output + ".cpp" if self.args.output else ""
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
        if self.args.output:
            if self._source_output_file is None:
                self._source_output_file = \
                        open(self.source_output_filepath(), "w")
            return self._source_output_file
        else:
            return sys.stdout
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

PHASE_CLASS_MEMBER              = 20
PHASE_CLASS_MEMBER_GETTER       = PHASE_CLASS_MEMBER + 1
PHASE_CLASS_MEMBER_CONST_GETTER = PHASE_CLASS_MEMBER + 2
PHASE_CLASS_MEMBER_SETTER       = PHASE_CLASS_MEMBER + 3
PHASE_CLASS_MEMBER_VARIABLE     = PHASE_CLASS_MEMBER + 4

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
    "std::vector" : {
        "include" : "<vector>"
    }
}

def refine_cpp_type(cpp_type):
    is_fundamental = True
    refined_parts = []
    for part in cpp_type.split(" "):
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

    if is_fundamental:
        refined_type = cpp_fundamental_types.get(" ".join(refined_parts), "")
        if not refined_type:
            raise RuntimeError("Failed to refined C++ type ({})".format(cpp_type))
        return refined_type
    else:
        return cpp_type
#enddef

class Context(object):

    def __init__(self, options):
        self._options = options
        self._out = None
        self._printers_data = {}
        self.__phases_stack = []
        self.__namespaces_stack = []
        self._used_types = []
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
        self.__phases_stack.append(phase)
        if phase == PHASE_HEADER_GEN:
            self._out = self._options.header_output_file()
        elif phase == PHASE_SOURCE_GEN:
            self._out = self._options.source_output_file()
    #enddef

    def end_phase(self, phase):
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

#endclass

class Printer(object):

    def __init__(self, context, node):
        self.__context = context
        self.__node = node
        self.__printers = []
        self.__parent = None

        assert(self.__node)
        assert(self.__context)
    #enddef

    @property
    def context(self):
        return self.__context
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

    def __generate_key(self):
        self_type = type(self)
        return "{0}{1}{2}".format(self_type.__module__,
                "." if self_type.__module__ else "", self_type.__name__)
    #enddef

    def write(self, *args):
        for arg in args:
            self.__context.out.write(str(arg))
    #enddef

    def writeln(self, *args):
        self.write(*args)
        print(file=self.__context.out)
    #enddef

#endclass

class NamespacePrinter(Printer):

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

        if self.context.in_phase(PHASE_HEADER_GEN):
            used_types = set(self.context.used_types)
            if used_types:
                for used_type in used_types:
                    include = cpp_types.get(used_type, {}).get("include", "")
                    if include:
                        self.write("#include ")
                        self.writeln(include)
        elif self.context.in_phase(PHASE_SOURCE_GEN):
            self.writeln("#include \"" + self.context.options.header_output_filename() + "\"")
        #endif

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

class ClassPrinter(Printer):

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
                #endclass data.node_attrs.cpp
            #endclass data.node_attrs
        #endclass data

        if not data.node_attrs.name:
            raise RuntimeError("Missing or empty 'name' attribute of a 'class' node")

        for printer in self.printers:
            data.node_attrs.cpp.pimpl |= printer.node.attributes.get("cpp", {}).get("pimpl", False)

        def generate_content(phases):
            if self.printers:
                if (self.context.in_phase(PHASE_CLASS_DECL) or self.context.in_phase(PHASE_CLASS_PIMPL_DECL)) \
                        and data.section != SECTION_PUBLIC:
                    self.writeln("public:")
                    data.section = SECTION_PUBLIC

                for printer in self.printers:
                    for phase in phases:
                        if (self.context.in_phase(PHASE_CLASS_DECL) or self.context.in_phase(PHASE_CLASS_PIMPL_DECL)) \
                                and phase == PHASE_CLASS_MEMBER_VARIABLE \
                                and data.section != SECTION_PRIVATE:
                            self.writeln("private:")
                            data.section = SECTION_PRIVATE

                        self.context.begin_phase(phase)

                        # FIXME This isn't sufficient, members will indicate that they didn't
                        # finished in the very beginning and it will be carried over through
                        # the whole process in the return value.
                        data.finished_flag &= printer.generate()

                        self.context.end_phase(phase)
                    #endfor
                #endfor
            #endif
        #enddef

        # TODO Structs isn't supported properly, generated as classes at the moment.

        if self.context.in_phase(PHASE_HEADER_GEN):
            self.context.begin_phase(PHASE_CLASS_DECL)
            self.writeln("struct " if data.node_attrs.is_struct else "class ", data.node_attrs.name)
            self.writeln("{")
            # Constructor & destructor.
            if data.node_attrs.cpp.pimpl:
                if data.section != SECTION_PUBLIC:
                    self.writeln("public:")
                    data.section = SECTION_PUBLIC
                self.writeln("  {}();".format(data.node_attrs.name))
                self.writeln("  virtual ~{}();".format(data.node_attrs.name))
            else:
                self.writeln("  virtual ~{}();".format(data.node_attrs.name))

            generate_content([ PHASE_CLASS_MEMBER_GETTER,
                               PHASE_CLASS_MEMBER_CONST_GETTER,
                               PHASE_CLASS_MEMBER_SETTER ])
            generate_content([ PHASE_CLASS_MEMBER_VARIABLE ])

            if data.node_attrs.cpp.pimpl:
                self.writeln("private:")
                self.writeln("  class Impl;")
                self.writeln("  Impl* m_impl = nullptr;")

            self.writeln("};")
            self.context.end_phase(PHASE_CLASS_DECL)
            data.finished_flag = PRINTER_NOT_FINISHED

        if self.context.in_phase(PHASE_SOURCE_GEN):
            if data.node_attrs.cpp.pimpl:
                # Declare pimpl class.
                data.section = SECTION_NONE
                self.context.begin_phase(PHASE_CLASS_PIMPL_DECL)
                self.writeln("class ", data.node_attrs.name, "::Impl")
                self.writeln("{")

                generate_content([ PHASE_CLASS_MEMBER_GETTER,
                                   PHASE_CLASS_MEMBER_CONST_GETTER,
                                   PHASE_CLASS_MEMBER_SETTER ])
                generate_content([ PHASE_CLASS_MEMBER_VARIABLE ])

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
                self.writeln("  : m_impl(new Impl)")
                self.writeln("{")
                self.writeln("}")
                self.writeln("{name}::~{name}()".format(name=data.node_attrs.name))
                self.writeln("{")
                self.writeln("  delete m_impl;")
                self.writeln("  m_impl = nullptr;")
                self.writeln("}")
            else:
                self.writeln("{name}::~{name}()".format(name=data.node_attrs.name))
                self.writeln("{")
                self.writeln("}")

            generate_content([ PHASE_CLASS_MEMBER_GETTER,
                               PHASE_CLASS_MEMBER_CONST_GETTER,
                               PHASE_CLASS_MEMBER_SETTER ])

            self.context.end_phase(PHASE_CLASS_IMPL)

        return data.finished_flag
    #enddef

#endclass

class ClassMemberPrinter(Printer):

    def __init__(self, context, node):
        super(ClassMemberPrinter, self).__init__(context, node)

        self._base_type = refine_cpp_type(node.attributes.get("type", ""))
        self._is_repeated = node.attributes.get("is_repeated", False)
        self._type = "std::vector<{}>".format(self._base_type) if self._is_repeated else self._base_type
        self._type_is_fundamental = not self._is_repeated and self._base_type in cpp_fundamental_types
        self._default = "" if not self._type_is_fundamental else "false" if self._type == "bool" else "0"

        if self._is_repeated:
            self.context.used_types.append("std::vector")
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
                    self.writeln("  {} {}() const;".format(self._type, self.node.attributes.get("name", "")))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    # TODO Also consider R-value for move semantic.
                    self.writeln("  void {}({} value);".format(self.node.attributes.get("name", ""), self._type))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_VARIABLE:
                    if not pimpl:
                        # TODO Initialization (default value).
                        self.write("  {} m_{}".format(self._type, self.node.attributes.get("name", "")))
                        if self._default:
                            self.write(" = {}".format(self._default))
                        self.writeln(";")
                else:
                    raise Exception("ClassMemberPrinter used in unsupported phase ({})".format(self.context.current_phase))
            else:
                if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                    # TODO Use format() in a better way (arguments could be preparend in advance).
                    # TODO Use ''' style string.
                    self.writeln("  {}& {}();".format(self._type, self.node.attributes.get("name", "")))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_CONST_GETTER:
                    self.writeln("  const {}& {}() const;".format(self._type, self.node.attributes.get("name", "")))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    # TODO Also consider R-value for move semantic.
                    self.writeln("  void {}({} value);".format(self.node.attributes.get("name", ""), self._type))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_VARIABLE:
                    if not pimpl:
                        # TODO Initialization (default value).
                        self.writeln("  {} m_{};".format(self._type, self.node.attributes.get("name", "")))
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
                    self.writeln("{} {}::{}() const".format(self._type, self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", "")))
                    self.writeln("{")
                    if not pimpl:
                        self.writeln("  return m_{};".format(self.node.attributes.get("name", "")))
                    else:
                        self.writeln("  return m_impl->{}();".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    # TODO Also consider R-value for move semantic.
                    self.writeln("void {}::{}({} value)".format(self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", ""), self._type))
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
                    self.writeln("{}& {}::{}()".format(self._type, self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", "")))
                    self.writeln("{")
                    if not pimpl:
                        self.writeln("  return m_{};".format(self.node.attributes.get("name", "")))
                    else:
                        self.writeln("  return m_impl->{}();".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                elif self.context.current_phase == PHASE_CLASS_MEMBER_CONST_GETTER:
                    self.writeln("const {}& {}::{}() const".format(self._type, self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", "")))
                    self.writeln("{")
                    if not pimpl:
                        self.writeln("  return m_{};".format(self.node.attributes.get("name", "")))
                    else:
                        self.writeln("  return m_impl->{}();".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    # TODO Also consider R-value for move semantic.
                    self.writeln("void {}::{}({} value)".format(self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", ""), self._type))
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
                    self.writeln("  {} {}() const;".format(self._type, self.node.attributes.get("name", "")))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    self.writeln("  void {}({} value);".format(self.node.attributes.get("name", ""), self._type))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_VARIABLE:
                    self.write("  {} m_{}".format(self._type, self.node.attributes.get("name", "")))
                    if self._default:
                        self.write(" = {}".format(self._default))
                    self.writeln(";")
                else:
                    raise Exception("ClassMemberPrinter used in unsupported phase ({})".format(self.context.current_phase))
            else:
                if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                    self.writeln("  {}& {}();".format(self._type, self.node.attributes.get("name", "")))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_CONST_GETTER:
                    pass
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    self.writeln("  void {}({} value);".format(self.node.attributes.get("name", ""), self._type))
                elif self.context.current_phase == PHASE_CLASS_MEMBER_VARIABLE:
                    self.writeln("  {} m_{};".format(self._type, self.node.attributes.get("name", "")))
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
                    self.writeln("{} {}::Impl::{}() const".format(self._type, self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", "")))
                    self.writeln("{")
                    self.writeln("  return m_{};".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    self.writeln("void {}::Impl::{}({} value)".format(self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", ""), self._type))
                    self.writeln("{")
                    self.writeln("  m_{} = value;".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                else:
                    raise Exception("ClassMemberPrinter used in unsupported phase ({})".format(self.context.current_phase))
            else:
                if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                    self.writeln("{}& {}::Impl::{}()".format(self._type, self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", "")))
                    self.writeln("{")
                    self.writeln("  return m_{};".format(self.node.attributes.get("name", "")))
                    self.writeln("}")
                elif self.context.current_phase == PHASE_CLASS_MEMBER_CONST_GETTER:
                    pass
                elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                    self.writeln("void {}::Impl::{}({} value)".format(self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", ""), self._type))
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

    def __init__(self, args=None):
        super(Generator, self).__init__()

        self._context = Context(Options(args))
        self._printers_stack = []
    #enddef

    def visit_package(self, node):
        self._printers_stack.append(NamespacePrinter(self._context, node))

        super(Generator, self).visit_package(node)

        self._finalize_printer(self._printers_stack.pop())
    #enddef

    def visit_class(self, node):
        self._printers_stack.append(ClassPrinter(self._context, node))

        super(Generator, self).visit_class(node)

        self._finalize_printer(self._printers_stack.pop())
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
        # FIXME This won't be always true. Parent printer probablu know what printer
        # to instanitate.
        self._printers_stack.append(ClassMemberPrinter(self._context, node))

        super(Generator, self).visit_attribute(node)

        self._finalize_printer(self._printers_stack.pop())
    #enddef

    def _finalize_printer(self, printer):
        if not self._printers_stack:
            # The last printer (the root one), output the code.
            for phase in [ PHASE_HEADER_GEN, PHASE_SOURCE_GEN ]:
                self._context.begin_phase(phase)
                if printer.generate() == PRINTER_FINISHED:
                    break
                self._context.end_phase(phase)
        else:
            # Not everything finalized yet, continue.
            self._printers_stack[-1].add_printer(printer)
    #enddef

#endclass
