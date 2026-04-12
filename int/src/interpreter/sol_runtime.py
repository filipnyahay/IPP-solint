"""
This modeule contains all necessary classes and fucntions to setup
and maintain the runtime

Author: Filip Nyahay, xnyahaf00
"""
from interpreter.input_model import Program
from interpreter.input_model import Method


class SOLClass:
    """Representation of SOL class"""
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.methods: dict[str, SOLMethod] = {}

    def __str__(self):
        methods_strs = {}

        cls = self
        while cls:
            for name, method in cls.methods.items():
                if name not in methods_strs:
                    methods_strs[name] = method
            cls = cls.parent

        methods_str = "\n".join(str(m) for m in methods_strs)
        return f"{self.name}\nmethods:\n{methods_str}"

    def add_method(self, selector: str, ast_node=None, builtin=None,  is_class_method=False):
        self.methods[selector] = SOLMethod(selector, ast_node, builtin, is_class_method)

    def method_lookup(self, selector: str):
        if selector in self.methods:
            return self.methods[selector]

        if self.parent:
            return self.parent.method_lookup(selector)

        return None

class SOLInstance:
    """Representation of an instance of SOL class"""
    def __init__(self, sol_cls: SOLClass, value=None):
        self.sol_cls: SOLClass = sol_cls
        self.instance_attrs = {}
        self._builtin_val = value

    def method_lookup(self, selector: str):
        return self.sol_cls.method_lookup(selector)

class SOLBlock(SOLInstance):
    def __init__(self, sol_cls, ast_node, params, env):
        super().__init__(sol_cls)
        self.ast_block = ast_node
        self.params = params
        self.env = env

class SOLMethod:
    def __init__(self, name, ast_node=None, builtin=None, is_class_method=False):
        self.name = name
        self.ast_node: Method = ast_node
        self.builtin = builtin
        self.is_class_method = is_class_method

    def __str__(self):
        kind = "builtin" if self.builtin is not None else "user"
        return f"{self.name} ({kind})"

    def is_builtin(self):
        return self.builtin is not None

class SOLRuntime:
    """Created at start of program, holds information about defined classes"""
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.classes: dict[str, SOLClass] = {}
        self.classes["Object"] = sol_obj()
        base_obj: SOLClass = self.classes["Object"]
        self.classes["Nil"] = sol_nil(base_obj)
        self._nil = self.call_method(self.classes["Nil"], "new", [])
        self.classes["Integer"] = sol_integer(base_obj)
        self.classes["String"] = sol_string(base_obj)
        self.classes["True"] = sol_true(base_obj)
        self.classes["False"] = sol_false(base_obj)
        self._true = self.call_method(self.classes["True"], "new", [])
        self._false = self.call_method(self.classes["False"], "new", [])
        self.classes["Block"] = sol_block(base_obj)

    def get_class(self, sol_class_name: str):
        return self.classes[sol_class_name]

    def call_method(self, receiver, selector: str, args: list[SOLInstance]):
        method = receiver.method_lookup(selector)

        if method is None:
            raise Exception("does not understand")

        if method.is_builtin():
            return method.builtin(self, receiver, args)

        # return self.interpreter.execute_user_method(method, receiver, args)
        return None

    def new_nil(self):
        return self._nil

    def new_integer(self, value: int):
        int_class = self.get_class("Integer")
        new_instance = self.call_method(int_class, "new", [])
        new_instance._builtin_val = value
        return new_instance

    def new_string(self, value: str):
        str_class = self.get_class("String")
        new_instance = self.call_method(str_class, "new", [])
        new_instance._builtin_val = value
        return new_instance

    def new_true(self):
        return self._true

    def new_false(self):
        return self._false

    def new_block(self, ast_node, env):
        block_class = self.get_class("Block")
        new_instance = self.call_method(block_class, "new", [])
        new_instance.ast_node = ast_node
        new_instance.env = env
        return new_instance

class Environment:
    """Local scope of a block or a method"""
    def __init__(self, parent=None):
        self.vars: dict[str, SOLInstance] = {}
        self.parent = parent

def sol_obj_new(runtime, cls, args):
    # print(f"Creating a SOLInstance of {cls}")
    return SOLInstance(cls)

def sol_obj_from(runtime, cls, args):
    pass

def sol_obj_as_string(runtime, receiver, args):
    return runtime.new_string("")

def sol_obj_is_number(runtime, receiver, args):
    return runtime._false

def sol_obj_is_string(runtime, receiver, args):
    return runtime._false

def sol_obj_is_block(runtime, receiver, args):
    return runtime._false

def sol_obj_is_nil(runtime, receiver, args):
    return runtime._false

def sol_obj_is_boolean(runtime, receiver, args):
    return runtime._false

def sol_obj_debug(runtime, receiver, args):
    print("this is a method from Object class")
    return receiver

def sol_obj():
    sol_obj = SOLClass("Object")
    sol_obj.add_method("new", builtin=sol_obj_new, is_class_method=True)
    sol_obj.add_method("from", builtin=sol_obj_from, is_class_method=True)
    sol_obj.add_method("asString", builtin=sol_obj_as_string)
    sol_obj.add_method("isNumber", builtin=sol_obj_is_number)
    sol_obj.add_method("isString", builtin=sol_obj_is_string)
    sol_obj.add_method("isBlock", builtin=sol_obj_is_block)
    sol_obj.add_method("isNil", builtin=sol_obj_is_nil)
    sol_obj.add_method("isBoolean", builtin=sol_obj_is_boolean)
    sol_obj.add_method("debug", builtin=sol_obj_debug)
    return sol_obj

def sol_nil_as_string(runtime, receiver: SOLInstance, args):
    return runtime.new_string("nil")

def sol_nil(sol_obj: SOLClass):
    sol_nil = SOLClass("Nil", sol_obj)
    sol_nil.add_method("asString", builtin=sol_nil_as_string)
    return sol_nil

def sol_integer_greater_than(runtime, receiver: SOLInstance, operand: SOLInstance):
    return receiver._builtin_val > operand._builtin_val

def sol_integer_plus(runtime, receiver: SOLInstance, operand: SOLInstance):
    receiver._builtin_val += operand._builtin_val
    return receiver

def sol_integer_minus(runtime, receiver: SOLInstance, operand: SOLInstance):
    receiver._builtin_val -= operand._builtin_val
    return receiver

def sol_integer_multiply_by(runtime, receiver: SOLInstance, operand: SOLInstance):
    receiver._builtin_val *= operand._builtin_val
    return receiver

def sol_integer_div_by(runtime, receiver: SOLInstance, operand: SOLInstance):
    if operand._builtin_val == 0:
        # TODO: interpreter error
        raise Exception("51")
    receiver._builtin_val = int(receiver._builtin_val / operand._builtin_val)
    return receiver

def sol_integer_as_string(runtime, receiver: SOLInstance, args):
    return runtime.new_string(str(receiver._builtin_val))

def sol_integer_as_integer(runtime, receiver: SOLInstance, args):
    return receiver

def sol_integer_times_repeat(runtime, receiver: SOLInstance, args):
    # TODO:
    pass

def sol_integer(sol_obj: SOLClass):
    sol_integer = SOLClass("Integer", sol_obj)
    sol_integer.add_method("greaterThan:", builtin=sol_integer_greater_than)
    sol_integer.add_method("plus:", builtin=sol_integer_plus)
    sol_integer.add_method("minus:", builtin=sol_integer_minus)
    sol_integer.add_method("multiplyBy:", builtin=sol_integer_multiply_by)
    sol_integer.add_method("divBy:", builtin=sol_integer_div_by)
    sol_integer.add_method("asString", builtin=sol_integer_as_string)
    sol_integer.add_method("asInteger", builtin=sol_integer_as_integer)
    sol_integer.add_method("timesRepeat", builtin=sol_integer_times_repeat)
    return sol_integer

def sol_string_read(runtime, receiver: SOLInstance, args):
    return runtime.new_string(input())

def sol_string_print(runtime, receiver: SOLInstance, args):
    print(receiver._builtin_val)
    return receiver

def sol_string_as_string(runtime, receiver: SOLInstance, args):
    return receiver

def sol_string_as_integer(runtime, receiver: SOLInstance, args):
    return runtime.new_integer(int(receiver._builtin_val))

def sol_string_concatenate_with(runtime, receiver: SOLInstance, arg: SOLInstance):
    if arg[0].sol_cls.name != "String":
        # nil class
        return None
    return runtime.new_string(receiver._builtin_val + arg[0]._builtin_val)

def sol_string_starts_ends(runtime, receiver: SOLInstance, start, end):
    # TODO:
    pass

def sol_string_length(runtime, receiver: SOLInstance, args):
    return runtime.new_integer(len(receiver._builtin_val))

def sol_string(sol_obj: SOLClass):
    sol_string = SOLClass("String", sol_obj)
    sol_string.add_method("print", builtin=sol_string_print)
    sol_string.add_method("read", builtin=sol_string_read, is_class_method=True)
    sol_string.add_method("concatenateWith:", builtin=sol_string_concatenate_with)
    sol_string.add_method("startsWith:endsBefore:", builtin=sol_string_starts_ends)
    sol_string.add_method("length", builtin=sol_string_length)
    return sol_string

def sol_bool_is_boolean(runtime, receiver: SOLInstance, args):
    return runtime.new_true()

def sol_true_as_string(runtime, receiver: SOLInstance, args):
    return runtime.new_string("true")

def sol_true_not(runtime, receiver: SOLInstance, args):
    return runtime.new_false()

def sol_true_and(runtime, receiver: SOLInstance, args):
    pass

def sol_true_or(runtime, receiver: SOLInstance, args):
    return runtime.new_true()

def sol_bool_if_true_if_false(runtime, receiver: SOLInstance, args):
    pass

def sol_true(sol_obj: SOLClass):
    sol_true = SOLClass("True", sol_obj)
    sol_true.add_method("asString", builtin=sol_true_as_string)
    sol_true.add_method("not", builtin=sol_true_not)
    sol_true.add_method("and:", builtin=sol_true_and)
    sol_true.add_method("or:", builtin=sol_true_or)
    sol_true.add_method("ifTrue:ifFalse:", builtin=sol_bool_if_true_if_false)
    sol_true.add_method("isBoolean", builtin=sol_bool_is_boolean)
    return sol_true

def sol_false_as_string(runtime, receiver: SOLInstance, args):
    return runtime.new_string("false")

def sol_false_not(runtime, receiver: SOLInstance, args):
    return runtime.new_true()

def sol_false_and(runtime, receiver: SOLInstance, args):
    return runtime.new_false()

def sol_false_or(runtime, receiver: SOLInstance, args):
    pass

def sol_false(sol_obj: SOLClass):
    sol_false = SOLClass("False", sol_obj)
    sol_false.add_method("asString", builtin=sol_false_as_string)
    sol_false.add_method("not", builtin=sol_false_not)
    sol_false.add_method("and:", builtin=sol_false_and)
    sol_false.add_method("or:", builtin=sol_false_or)
    sol_false.add_method("ifTrue:ifFalse:", builtin=sol_bool_if_true_if_false)
    sol_false.add_method("isBoolean", builtin=sol_bool_is_boolean)
    return sol_false

def sol_block(sol_obj: SOLClass):
    return SOLClass("Block", sol_obj)
