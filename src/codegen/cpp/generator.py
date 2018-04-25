import sys, copy
import codemodel

options = {
    "outputFile": None
}

class Generator(codemodel.cpp.CppModelVisitor):

    def __init__(self, customOptions={}):
        super(CppCodeGenerator, self).__init__()

        self.options = copy.deepcopy(options)
        if customOptions:
            self.options.update(customOptions) 

        self.nsStack = []
        self.out = self.options["outputFile"]
        if not self.out:
            self.out = sys.stdout
    #enddef

    def visitCppNamespace(self, node):
        self.writeln("namespace ", node.name, " {")
        self.nsStack.append(node)
        super(CppCodeGenerator, self).visitCppNamespace(node)
        self.writeln("} // namespace ", "::".join(ns.name for ns in self.nsStack))
        self.nsStack.pop()
    #enddef

    def visitCppClass(self, node):
        self.writeln("struct " if node.struct else "class ", node.name, " {")
        super(CppCodeGenerator, self).visitCppClass(node)
        self.writeln("};")
    #enddef

    def visitCppMethod(self, node):
        self.writeln("static " if node.static else "", node.retval, " ", node.name,
            "(", ", ".join(node.params), ");")
        super(CppCodeGenerator, self).visitCppMethod(node)
    #enddef

    def write(self, *args):
        for arg in args:
            self.out.write(str(arg))
    #enddef

    def writeln(self, *args):
        self.write(*args)
        print >> self.out
    #enddef

#enddef
