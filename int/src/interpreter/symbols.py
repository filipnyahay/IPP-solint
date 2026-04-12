"""Author: Filip Nyahay, xnyahaf00"""
import interpreter.input_model as sol_ast


class SOLClassInfo:
    """Information about SOL26 class for purpose of static analysis"""
    def __init__(self, name: str):
        self.name: str = name
        self.methods: dict[str, SOLMethodInfo] = {}

class SOLMethodInfo:
    """Information about SOL26 method for purpose of static analysis"""
    def __init__(self, ast_node: sol_ast.Method):
        self.name: str = ast_node.selector
        self.arity: int = ast_node.block.arity
        self.block_info: SOLBlockInfo = SOLBlockInfo(ast_node.block)
        self.ast_node: sol_ast.Method = ast_node

class SOLBlockInfo:
    """Information about SOL26 block for purpose of static analysis"""
    def __init__(self, ast_node: sol_ast.Block):
        self.params: list[str] = [param.name for param in ast_node.parameters]
        self.vars: list[str] = [ assign.target.name for assign in ast_node.assigns]
