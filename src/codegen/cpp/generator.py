import sys, copy
import codemodel

options = {
    "output_file": None
}

PHASE_NONE = -1

PHASE_HEADER_GEN = 0
PHASE_SOURCE_GEN = 1

PHASE_CLASS_GEN                     = 10
PHASE_CLASS_GEN_MEMBER_GETTER       = PHASE_CLASS_GEN + 1
PHASE_CLASS_GEN_MEMBER_CONST_GETTER = PHASE_CLASS_GEN + 2
PHASE_CLASS_GEN_MEMBER_SETTER       = PHASE_CLASS_GEN + 3
PHASE_CLASS_GEN_MEMBER_VARIABLE     = PHASE_CLASS_GEN + 4

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
        return self.__printers
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
        finished_flag = PRINTER_FINISHED

        name = self.node.attributes.get("name", "")
        is_struct = self.node.attributes.get("is_struct", False)

        if not name:
            raise RuntimeError("Missing or empty 'name' attribute of a 'class' node")

        self.writeln("struct " if is_struct else "class ", name)
        self.writeln("{")

        if self.printers:
            self.writeln("public:")
            for phase in  [ PHASE_CLASS_GEN_MEMBER_GETTER, PHASE_CLASS_GEN_MEMBER_CONST_GETTER,
                            PHASE_CLASS_GEN_MEMBER_SETTER, PHASE_CLASS_GEN_MEMBER_VARIABLE ]:
                if phase == PHASE_CLASS_GEN_MEMBER_VARIABLE:
                    self.writeln("private:")

                self.context.begin_phase(phase)

                for printer in self.printers:
                    finished_flag &= printer.generate()

                self.context.end_phase(phase)

        self.writeln("};")

        return finished_flag
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

        # TODO Use context for passing the current phase.
        if self.context.current_phase == PHASE_CLASS_GEN_MEMBER_GETTER:
            # TODO Distinguish between types ('value' vs. 'reference' type).
            # TODO Use format() in a better way (arguments could be preparend in advance).
            # TODO Use ''' style string.
            self.writeln("  {}& {}()".format(resolve_type(), self.node.attributes.get("name", "")))
            self.writeln("  {")
            self.writeln("    return m_{};".format(self.node.attributes.get("name", "")))
            self.writeln("  }")
        elif self.context.current_phase == PHASE_CLASS_GEN_MEMBER_CONST_GETTER:
            self.writeln("  const {}& {}() const".format(resolve_type(), self.node.attributes.get("name", "")))
            self.writeln("  {")
            self.writeln("    return m_{};".format(self.node.attributes.get("name", "")))
            self.writeln("  }")
        elif self.context.current_phase == PHASE_CLASS_GEN_MEMBER_SETTER:
            # TODO Also consider R-value for move semantic.
            self.writeln("  void {}(const {}& value)".format(self.node.attributes.get("name", ""), resolve_type()))
            self.writeln("  {")
            self.writeln("    m_{} = value;".format(self.node.attributes.get("name", "")))
            self.writeln("  }")
        elif self.context.current_phase == PHASE_CLASS_GEN_MEMBER_VARIABLE:
            # TODO Initialization (default value).
            self.writeln("  {} m_{};".format(resolve_type(), self.node.attributes.get("name", "")))
        else:
            raise Exception("ClassMemberPrinter in wrong context")

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
                if printer.generate() == PRINTER_FINISHED:
                    break
        else:
            # Not everything finalized yet, continue.
            self._printers_stack[-1].printers.append(printer)
    #enddef

#endclass
