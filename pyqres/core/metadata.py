from typing import Dict, List, Union

from sympy import Symbol


class RegisterMetadata:
    """Quantum register metadata manager."""

    def __init__(self):
        self.registers: Dict[str, Union[int, Symbol]] = {}
        self.register_types: Dict[str, str] = {}

    def __str__(self):
        return f"Registers: {self.registers}"

    def declare_register(self, name, size, reg_type="General"):
        if name in self.registers:
            if size == self.registers[name]:
                return
            raise ValueError(f"Register {name} already declared")
        self.registers[name] = size
        self.register_types[name] = reg_type

    def declare_registers(self, regs):
        for entry in regs:
            if len(entry) == 3:
                reg, size, reg_type = entry
            else:
                reg, size = entry
                reg_type = "General"
            self.declare_register(reg, size, reg_type)

    def undeclare_register(self, name):
        if name not in self.registers:
            raise ValueError(f"Register {name} not declared")
        del self.registers[name]
        self.register_types.pop(name, None)

    def undeclare_registers(self, regs):
        for reg in regs:
            self.undeclare_register(reg)

    def split_register(self, reg, new_reg_declarations):
        if reg not in self.registers:
            raise ValueError(f"Register {reg} not declared")
        old_size = self.registers[reg]
        for name, size in new_reg_declarations:
            if name not in self.registers:
                self.declare_register(name, size)
            if isinstance(size, int) and isinstance(old_size, int) and size > old_size:
                raise ValueError(f"Register {reg} size too small to split")
            self.registers[name] = size
            if old_size is not None:
                old_size -= size
        self.registers[reg] = old_size

    def merge_register(self, reg, regs_to_merge):
        if reg not in self.registers:
            raise ValueError(f"Register {reg} not declared")
        new_size = self.registers[reg]
        for r in regs_to_merge:
            if new_size is not None:
                new_size += self.registers[r]
            self.registers[r] = 0
        self.registers[reg] = new_size

    # Class-level stack for nested scopes
    register_metadata_stack: List['RegisterMetadata'] = []

    @staticmethod
    def get_register_metadata() -> 'RegisterMetadata':
        if not RegisterMetadata.register_metadata_stack:
            RegisterMetadata.register_metadata_stack.append(RegisterMetadata())
        return RegisterMetadata.register_metadata_stack[-1]

    @staticmethod
    def push_register_metadata() -> 'RegisterMetadata':
        RegisterMetadata.register_metadata_stack.append(RegisterMetadata())
        return RegisterMetadata.register_metadata_stack[-1]

    @staticmethod
    def pop_register_metadata():
        if not RegisterMetadata.register_metadata_stack:
            raise ValueError("Register metadata stack is empty")
        RegisterMetadata.register_metadata_stack.pop()

    @staticmethod
    def add_register(reg):
        RegisterMetadata.get_register_metadata().declare_register(reg)

    @staticmethod
    def add_registers(regs):
        RegisterMetadata.get_register_metadata().declare_registers(regs)

    @staticmethod
    def remove_register(reg):
        RegisterMetadata.get_register_metadata().undeclare_register(reg)

    @staticmethod
    def remove_registers(regs):
        RegisterMetadata.get_register_metadata().undeclare_registers(regs)

    @staticmethod
    def get_registers():
        return RegisterMetadata.get_register_metadata().registers

    @staticmethod
    def get_register_types():
        return RegisterMetadata.get_register_metadata().register_types


class ProgramMetadata:
    """Quantum program metadata manager."""

    def __init__(self):
        self.qfunctions: Dict[str, 'FunctionDeclaration'] = {}

    def declare_qfunction(self, name, reg_count, param_count=0,
                         temp_reg_count=0, submodule_count=0):
        if name in self.qfunctions:
            return
        self.qfunctions[name] = FunctionDeclaration(
            name, reg_count, param_count, temp_reg_count, submodule_count)

    def declare_program_list(self, name, program_list):
        if name in self.qfunctions:
            self.qfunctions[name].program_list = program_list

    def __str__(self):
        ret = "Program Metadata:\n"
        for name, func in self.qfunctions.items():
            ret += f"  {func}\n"
        return ret

    def quantikz(self, path=None):
        # TODO: no maintain until refactoring
        pass


program_metadata = ProgramMetadata()


class FunctionDeclaration:
    """Quantum function declaration with metadata."""

    def __init__(self, name, reg_count, param_count=0, temp_reg_count=0,
                 submodule_count=0, reg_size_limit=None, program_list=None):
        self.name = name
        self.reg_count = reg_count
        self.param_count = param_count
        self.temp_reg_count = temp_reg_count
        self.submodule_count = submodule_count
        self.reg_size_limit = [None] * reg_count if reg_size_limit is None else reg_size_limit
        self.program_list = program_list or []

    def __str__(self):
        mock_register_metadata = RegisterMetadata.push_register_metadata()
        regs = [f"q_{i}" for i in range(self.reg_count)]
        size_param = 0
        for i, reg in enumerate(regs):
            reg_size = self.reg_size_limit[i]
            if reg_size is None:
                reg_size_ = Symbol(f"d_{size_param}")
                size_param += 1
            else:
                reg_size_ = reg_size
            mock_register_metadata.declare_register(reg, reg_size_)

        params = [Symbol(f"p_{i}") for i in range(self.param_count)]

        qreg_decl_str = ", ".join(
            f"{reg}[{mock_register_metadata.registers[reg]}]" for reg in regs)
        param_decl_str = ", ".join(str(p) for p in params)

        ret = f"{self.name}: QRegs({qreg_decl_str})"
        if params:
            ret += f", Params({param_decl_str})"

        RegisterMetadata.pop_register_metadata()
        return ret
