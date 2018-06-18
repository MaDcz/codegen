import sys, copy
import codemodel

options = {
    "output_file": None
}

class Context(object):

    def __init__(self, out):
        self._out = out
        self._printers_data = {}
    #enddef

    @property
    def out(self):
        return self._out
    #enddef

    @property
    def printers_data(self):
        return self._printers_data
    #enddef

#endclass

class Printer(object):

    def __init__(self, context):
        self.__context = context
        self.__printers = []
    #enddef

    @property
    def context(self):
        self_key = self.__generate_key()
        if self_key not in self.__context.printers_data:
            self.__context.printers_data[self_key] = {}

        return self.__context.printers_data[self_key]
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
        super(NamespacePrinter, self).__init__(context)
        self._node = node
    #enddef

    def generate(self, parent_phase = -1):
        context = self.context
        # TODO Better to have static variable for this.
        if "ns_stack" not in context:
            context["ns_stack"] = []

        # TODO Do a special node for the root node.
        name = self._node.attributes.get("name", "")
        if name:
            self.writeln("namespace ", name, " {")
            context["ns_stack"].append(self._node)

        # TODO Move this to the base where printers property will be better encapsulated.
        for printer in self.printers:
            printer.generate(parent_phase)

        if name:
            self.writeln("} // namespace ", "::".join(ns.attributes["name"] for ns in context["ns_stack"]))
            context["ns_stack"].pop()
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

    # The phases will need to be global.
    CLASS_GEN_MEMBER_GETTER = 0
    CLASS_GEN_MEMBER_CONST_GETTER = 1
    CLASS_GEN_MEMBER_SETTER = 2
    CLASS_GEN_MEMBER_VARIABLE = 3
    CLASS_GEN_CNT = 4

    def __init__(self, context, node):
        super(ClassPrinter, self).__init__(context)
        self._node = node
    #enddef

    def generate(self, parent_phase = -1):
        name = self._node.attributes.get("name", "")
        is_struct = self._node.attributes.get("is_struct", False)

        if not name:
            raise RuntimeError("Missing or empty 'name' attribute of a 'class' node")

        self.writeln("struct " if is_struct else "class ", name)
        self.writeln("{")

        if self.printers:
            self.writeln("public:")
            for phase in range(self.CLASS_GEN_CNT):
                if phase == self.CLASS_GEN_MEMBER_VARIABLE:
                    self.writeln("private:")

                for printer in self.printers:
                    printer.generate(phase)

        self.writeln("};")
    #enddef

#endclass

class ClassMemberPrinter(Printer):

    def __init__(self, context, node):
        super(ClassMemberPrinter, self).__init__(context)
        self._node = node # TODO Move to the base too.
    #enddef

    def generate(self, parent_phase = -1):
        def resolve_type():
            return "std::vector<{}>".format(self._node.attributes.get("type", "")) \
                    if self._node.attributes.get("is_repeated", False) \
                    else self._node.attributes.get("type", "")
        #enddef

        # TODO Use context for passing the current phase.
        if parent_phase == ClassPrinter.CLASS_GEN_MEMBER_GETTER:
            # TODO Distinguish between types ('value' vs. 'reference' type).
            # TODO Use format() in a better way (arguments could be preparend in advance).
            # TODO Use ''' style string.
            self.writeln("  {}& {}()".format(resolve_type(), self._node.attributes.get("name", "")))
            self.writeln("  {")
            self.writeln("    return m_{};".format(self._node.attributes.get("name", "")))
            self.writeln("  }")
        elif parent_phase == ClassPrinter.CLASS_GEN_MEMBER_CONST_GETTER:
            self.writeln("  const {}& {}() const".format(resolve_type(), self._node.attributes.get("name", "")))
            self.writeln("  {")
            self.writeln("    return m_{};".format(self._node.attributes.get("name", "")))
            self.writeln("  }")
        elif parent_phase == ClassPrinter.CLASS_GEN_MEMBER_SETTER:
            # TODO Also consider R-value for move semantic.
            self.writeln("  void {}(const {}& value)".format(self._node.attributes.get("name", ""), resolve_type()))
            self.writeln("  {")
            self.writeln("    m_{} = value;".format(self._node.attributes.get("name", "")))
            self.writeln("  }")
        elif parent_phase == ClassPrinter.CLASS_GEN_MEMBER_VARIABLE:
            # TODO Initialization (default value).
            self.writeln("  {} m_{};".format(resolve_type(), self._node.attributes.get("name", "")))
        else:
            raise Exception("ClassMemberPrinter in wrong context")
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

        printer = self._printers_stack.pop()
        if self._printers_stack:
            self._printers_stack[-1].printers.append(printer)
        else:
            printer.generate()
    #enddef

    def visit_class(self, node):
        self._printers_stack.append(ClassPrinter(self._context, node))

        super(Generator, self).visit_class(node)

        printer = self._printers_stack.pop()
        if self._printers_stack:
            self._printers_stack[-1].printers.append(printer)
        else:
            printer.generate()
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

        printer = self._printers_stack.pop()
        if self._printers_stack:
            self._printers_stack[-1].printers.append(printer)
        else:
            printer.generate()
    #enddef

#endclass
