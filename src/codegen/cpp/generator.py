import sys, copy
import codemodel

options = {
    "output_file": None
}

class Generator(codemodel.ClassDiagramVisitor):

    def __init__(self, custom_options={}):
        super(Generator, self).__init__()

        self.options = copy.deepcopy(options)
        if custom_options:
            self.options.update(custom_options) 

        self.ns_stack = []
        self.out = self.options["output_file"]
        if not self.out:
            self.out = sys.stdout
    #enddef

    def visit_package(self, node):
        # TODO Do a special node for the root node.
        name = node.attributes.get("name", "")
        if name:
            self.writeln("namespace ", name, " {")
            self.ns_stack.append(node)
        super(Generator, self).visit_package(node)
        if name:
            self.writeln("} // namespace ", "::".join(ns.attributes["name"] for ns in self.ns_stack))
            self.ns_stack.pop()
    #enddef

    def visit_class(self, node):
        name = node.attributes.get("name", "")
        is_struct = node.attributes.get("is_struct", False)

        if not name:
            raise RuntimeError("Missing or empty 'name' attribute of a 'class' node")

        self.writeln("struct " if is_struct else "class ", name, " {")
        super(Generator, self).visit_class(node)
        self.writeln("};")
    #enddef

    def visit_operation(self, node):
        name = node.attributes.get("name", "")
        return_type = node.attributes.get("return_type", "void")
        params = node.attributes.get("params", [])
        is_static = node.attributes.get("is_static", False)

        if not name:
            raise RuntimeError("Missing or empty 'name' attribute of a 'operation' node")

        self.writeln("static " if is_static else "", return_type, " ", name,
            "(", ", ".join(params), ");")
        super(Generator, self).visit_operation(node)
    #enddef

    def write(self, *args):
        for arg in args:
            self.out.write(str(arg))
    #enddef

    def writeln(self, *args):
        self.write(*args)
        print(file=self.out)
    #enddef

#endclass
