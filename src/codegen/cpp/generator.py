import sys, copy
import codemodel

options = {
    "output_file": None
}

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

class Context(object):

    def __init__(self, out):
        self._out = out
        self._printers_data = {}
        self.__phases_stack = []
        self.__namespaces_stack = []
    #enddef

    @property
    def out(self):
        return self._out
    #enddef

    @property
    def printers_data(self):
        return self._printers_data
    #enddef

    def begin_phase(self, phase):
        self.__phases_stack.append(phase)
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

        self.context.begin_phase(PHASE_CLASS_DECL)
        self.writeln("struct " if data.node_attrs.is_struct else "class ", data.node_attrs.name)
        self.writeln("{")
        if data.node_attrs.cpp.pimpl:
            if data.section != SECTION_PUBLIC:
                self.writeln("public:")
                data.section = SECTION_PUBLIC
            self.writeln("  {}()".format(data.node_attrs.name))
            self.writeln("    : m_impl(new Impl)")
            self.writeln("  {")
            self.writeln("  }")

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

        if data.node_attrs.cpp.pimpl:
            # Declare pimpl class.
            data.section = SECTION_NONE
            self.context.begin_phase(PHASE_CLASS_PIMPL_DECL)
            self.writeln("class ", data.node_attrs.name, "::Impl")
            self.writeln("{")

            generate_content([ PHASE_CLASS_MEMBER_GETTER,
                               PHASE_CLASS_MEMBER_SETTER ])
            generate_content([ PHASE_CLASS_MEMBER_VARIABLE ])

            self.writeln("};")
            self.context.end_phase(PHASE_CLASS_PIMPL_DECL)

            # Implement pimpl class methods.
            self.context.begin_phase(PHASE_CLASS_PIMPL_IMPL)

            generate_content([ PHASE_CLASS_MEMBER_GETTER,
                               PHASE_CLASS_MEMBER_SETTER ])

            self.context.end_phase(PHASE_CLASS_PIMPL_IMPL)
        #endif

        self.context.begin_phase(PHASE_CLASS_IMPL)

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
    #enddef

    def generate(self):
        finished_flag = PRINTER_FINISHED

        def resolve_type():
            return "std::vector<{}>".format(self.node.attributes.get("type", "")) \
                    if self.node.attributes.get("is_repeated", False) \
                    else self.node.attributes.get("type", "")
        #enddef

        pimpl = self.node.attributes.get("cpp", {}).get("pimpl", None)
        if pimpl is None:
            pimpl = self.parent.node.attributes.get("cpp", {}).get("pimpl", False)

        def generate_class_decl():
            # TODO The following applies only for class-like types.
            if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                # TODO Distinguish between types ('value' vs. 'reference' type).
                # TODO Use format() in a better way (arguments could be preparend in advance).
                # TODO Use ''' style string.
                self.writeln("  {}& {}();".format(resolve_type(), self.node.attributes.get("name", "")))
            elif self.context.current_phase == PHASE_CLASS_MEMBER_CONST_GETTER:
                self.writeln("  const {}& {}() const;".format(resolve_type(), self.node.attributes.get("name", "")))
            elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                # TODO Also consider R-value for move semantic.
                self.writeln("  void {}(const {}& value);".format(self.node.attributes.get("name", ""), resolve_type()))
            elif self.context.current_phase == PHASE_CLASS_MEMBER_VARIABLE:
                if not pimpl:
                    # TODO Initialization (default value).
                    self.writeln("  {} m_{};".format(resolve_type(), self.node.attributes.get("name", "")))
            else:
                raise Exception("ClassMemberPrinter used in unsupported phase ({})".format(self.context.current_phase))
        #enddef

        def generate_class_impl():
            # TODO The following applies only for class-like types.
            if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                # TODO Distinguish between types ('value' vs. 'reference' type).
                # TODO Use format() in a better way (arguments could be preparend in advance).
                # TODO Use ''' style string.
                self.writeln("{}& {}::{}()".format(resolve_type(), self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", "")))
                self.writeln("{")
                if not pimpl:
                    self.writeln("  return m_{};".format(self.node.attributes.get("name", "")))
                else:
                    self.writeln("  return m_impl->{}();".format(self.node.attributes.get("name", "")))
                self.writeln("}")
            elif self.context.current_phase == PHASE_CLASS_MEMBER_CONST_GETTER:
                self.writeln("const {}& {}::{}() const".format(resolve_type(), self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", "")))
                self.writeln("{")
                if not pimpl:
                    self.writeln("  return m_{};".format(self.node.attributes.get("name", "")))
                else:
                    self.writeln("  return m_impl->{}();".format(self.node.attributes.get("name", "")))
                self.writeln("}")
            elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                # TODO Also consider R-value for move semantic.
                self.writeln("void {}::{}(const {}& value)".format(self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", ""), resolve_type()))
                self.writeln("{")
                if not pimpl:
                    self.writeln("  m_{} = value;".format(self.node.attributes.get("name", "")))
                else:
                    self.writeln("  m_impl->{}(value);".format(self.node.attributes.get("name", "")))
                self.writeln("}")
            else:
                raise Exception("ClassMemberPrinter used in unsupported phase ({})".format(self.context.current_phase))
        #enddef

        def generate_pimpl_decl():
            if not pimpl:
                return

            # TODO The following applies only for class-like types.
            if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                self.writeln("  {}& {}();".format(resolve_type(), self.node.attributes.get("name", "")))
            elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                self.writeln("  void {}(const {}& value);".format(self.node.attributes.get("name", ""), resolve_type()))
            elif self.context.current_phase == PHASE_CLASS_MEMBER_VARIABLE:
                self.writeln("  {} m_{};".format(resolve_type(), self.node.attributes.get("name", "")))
            else:
                raise Exception("ClassMemberPrinter used in unsupported phase ({})".format(self.context.current_phase))
        #enddef

        def generate_pimpl_impl():
            if not pimpl:
                return

            # TODO The following applies only for class-like types.
            if self.context.current_phase == PHASE_CLASS_MEMBER_GETTER:
                self.writeln("{}& {}::Impl::{}()".format(resolve_type(), self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", "")))
                self.writeln("{")
                self.writeln("  return m_{};".format(self.node.attributes.get("name", "")))
                self.writeln("}")
            elif self.context.current_phase == PHASE_CLASS_MEMBER_SETTER:
                self.writeln("void {}::Impl::{}(const {}& value)".format(self.parent.node.attributes.get("name", ""), self.node.attributes.get("name", ""), resolve_type()))
                self.writeln("{")
                self.writeln("  m_{} = value;".format(self.node.attributes.get("name", "")))
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

    # XXX This is a good approeach, it's needed to first generate printers
    # tree from the class diagram and the output the code as there has to be
    # some tweaks between, like include neccesary headers.

    def __init__(self, custom_options={}):
        super(Generator, self).__init__()

        # TODO >>> Refactor this according to the latest changes.
        self.options = copy.deepcopy(options)
        if custom_options:
            self.options.update(custom_options)

        self.ns_stack = []
        self.out = self.options["output_file"]
        if not self.out:
            self.out = sys.stdout
        # TODO <<<

        self._context = Context(self.out)
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
