"""
This module contains the main logic of the interpreter.

IPP: You must definitely modify this file. Bend it to your will.

Author: Ondřej Ondryáš <iondryas@fit.vut.cz>
Author:
"""

import logging
from pathlib import Path
from typing import TextIO

from lxml import etree
from lxml.etree import ParseError
from pydantic import ValidationError

import interpreter.symbols as solsym
from interpreter.error_codes import ErrorCode
from interpreter.exceptions import InterpreterError
from interpreter.input_model import Assign, Block, Expr, Literal, Program
from interpreter.sol_runtime import Environment, SOLInstance, SOLMethod, SOLRuntime

logger = logging.getLogger(__name__)

class Interpreter:
    """
    The main interpreter class, responsible for loading the source file and executing the program.
    """

    def __init__(self) -> None:
        self.current_program: Program | None = None
        self.symtable: dict[str, solsym.SOLClassInfo] = {}
        self.runtime: SOLRuntime = SOLRuntime(self)

    def load_program(self, source_file_path: Path) -> None:
        """
        Reads the source SOL-XML file and stores it as the target program for this interpreter.
        If any program was previously loaded, it is replaced by the new one.

        IPP: If you wish to run static checks on the program before execution, this is a good place
             to call them from.
        """
        logger.info("Opening source file: %s", source_file_path)
        try:
            xml_tree = etree.parse(source_file_path)
        except ParseError as e:
            raise InterpreterError(
                error_code=ErrorCode.INT_XML, message="Error parsing input XML"
            ) from e
        try:
            self.current_program = Program.from_xml_tree(xml_tree.getroot())  # type: ignore
        except ValidationError as e:
            raise InterpreterError(
                error_code=ErrorCode.INT_STRUCTURE, message="Invalid SOL-XML structure"
            ) from e

        ### static analysis ###
        # collect class names, method names, and arity
        # semantic error 35 (class redefinition)
        for ast_class in self.current_program.classes:
            if ast_class.name in self.symtable:
                raise InterpreterError(
                    error_code=ErrorCode.SEM_ERROR, message=(
                        f"Static error: Class redefinition, class {ast_class.name} already exists"
                    )
                )
            self.symtable[ast_class.name] = solsym.SOLClassInfo(ast_class.name)
            methods_dict = self.symtable[ast_class.name].methods
            for ast_method in ast_class.methods:
                methods_dict[ast_method.selector] = solsym.SOLMethodInfo(ast_method)
        # semantic error 31
        if ("Main" not in self.symtable or "run" not in self.symtable["Main"].methods):
            raise InterpreterError(
                error_code=ErrorCode.SEM_MAIN, message=
                "Static error: No class Main or it's manadatory method run found"
            )
        # semantic error 33
        for cls_name in self.symtable:
            for sol_method_info in self.symtable[cls_name].methods.values():
                if sol_method_info.name.count(":") != sol_method_info.arity:
                    raise InterpreterError(
                        error_code=ErrorCode.SEM_ARITY, message=(
                        f"Static error: Arity doesnt match for method selector and block\n"
                        f"\tSelector {sol_method_info.name} expects arity of "
                        f"{sol_method_info.name.count(":")} and got {sol_method_info.arity}\n")
                    )
        # semantic error 34
        for cls_name in self.symtable:
            for sol_method_info in self.symtable[cls_name].methods.values():
                for var in sol_method_info.block_info.vars:
                    if var in sol_method_info.block_info.params:
                        raise InterpreterError(
                            error_code=ErrorCode.SEM_COLLISION,
                            message="Static error: Assignment to block's formal parameter"
                        )
    # wrappers for runtime instance creation
    def sol_nil(self):
        """Wrapper for creating an instance of Nil class, calls the runtime helper"""
        return self.runtime.new_nil()

    def sol_int(self, value: int):
        """Wrapper for creating an instance of Integer class, calls the runtime helper"""
        return self.runtime.new_integer(value)

    def sol_str(self, value: str):
        """Wrapper for creating an instance of String class, calls the runtime helper"""
        return self.runtime.new_string(value)

    def sol_true(self):
        """Wrapper for creating an instance of True class, calls the runtime helper"""
        return self.runtime.new_true()

    def sol_false(self):
        """Wrapper for creating an instance of False class, calls the runtime helper"""
        return self.runtime.new_false()

    def sol_block(self, ast_node, env):
        """
        Wrapper for creating an instance of Block class, calls the runtime helper
        Additional info in sol_runtime.py
        """
        return self.runtime.new_block(ast_node, env)

    def sol_send(self, receiver, selector: str, args):
        """Wrapper for sending messages, calls the runtime helper"""
        return self.runtime.call_method(receiver, selector, args)

    def execute_literal(self, ast_node: Literal):
        """Interprets AST Literal node"""
        if ast_node.class_id == "Integer":
            return self.sol_int(int(ast_node.value))
        if ast_node.class_id == "String":
            return self.sol_str(ast_node.value)
        if ast_node.class_id == "Nil":
            return self.sol_nil()
        if ast_node.class_id == "True":
            return self.sol_true()
        if ast_node.class_id == "False":
            return self.sol_false()
        if ast_node.class_id == "class":
            return self.runtime.get_class(ast_node.value)

        raise Exception("Unreachable")

    def execute_expr(self, ast_node: Expr, env):
        """Interprets AST Expr node"""
        if ast_node.literal is not None:
            return self.execute_literal(ast_node.literal)
        if ast_node.var is not None:
            return env.vars[ast_node.var.name]
        if ast_node.block is not None:
            return self.sol_block(ast_node.block, env)
        if ast_node.send is not None:
            msg_receiver = self.execute_expr(ast_node.send.receiver, env)
            msg_selector = ast_node.send.selector
            msg_args = [self.execute_expr(arg.expr, env) for arg in ast_node.send.args]
            return self.sol_send(msg_receiver, msg_selector, msg_args)

        raise Exception("Unreachable")

    def execute_assign(self, ast_node: Assign, env):
        """Interprets AST Assign node"""
        expr_res = self.execute_expr(ast_node.expr, env)
        env.vars[ast_node.target.name] = expr_res
        return expr_res

    def execute_block(self, ast_node: Block, env):
        """Interprets AST Block node"""
        result = self.sol_nil()
        for assign in ast_node.assigns:
            result = self.execute_assign(assign, env)

        return result

    def execute_user_method(self, method: SOLMethod, receiver: SOLInstance, args):
        """
        Interprets AST Method node
        Prepears it's Environment, binding params, and adding self
        """
        env = Environment()
        env.vars["self"] = receiver

        if method.ast_node.block.arity != len(args):
            raise InterpreterError(error_code=ErrorCode.INT_OTHER, message=(
                "Block arity doesn't match number of passed parameters"
            ))

        for i in range(len(args)):
            arg_name = method.ast_node.block.parameters[i].name
            env.vars[arg_name] = args[i]

        return self.execute_block(method.ast_node.block, env)


    def execute(self, input_io: TextIO) -> None:
        """
        Executes the currently loaded program, using the provided input stream as standard input.
        """
        logger.info("Executing program")

        for ast_class in self.current_program.classes:
            self.runtime.register_class(ast_class)

        main_class = self.runtime.get_class("Main")
        main_instance = self.sol_send(main_class, "new", [])
        self.sol_send(main_instance, "run", [])
