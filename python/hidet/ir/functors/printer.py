from collections import defaultdict
from hidet.ir.node import Node
from hidet.ir.func import IRModule, Function
from hidet.ir.type import ScalarType, TensorType, TypeNode
from hidet.ir.expr import Constant, Var, Call, TensorElement, Add, Multiply, Expr, LessThan, FloorDiv, Mod, Equal, Div, Sub, Not, Or, And, Let, IfThenElse
from hidet.ir.stmt import SeqStmt, IfStmt, ForStmt, LetStmt, AssignStmt, BufferStoreStmt, EvaluateStmt, Stmt, AssertStmt, BlackBoxStmt, AsmStmt, ReturnStmt, SeqLetStmt
from hidet.ir.task import Worker, Host, Grid, ThreadBlock, Warp, Thread
from hidet.ir.dialects.compute import ReduceCompute, TensorCompute, TensorInput, ScalarInput
from hidet.ir.dialects.lowlevel import VoidType, PointerType, Dereference, Cast, Address, ReferenceType, TensorPointerType, Reference
from hidet.ir.dialects.pattern import AnyExpr, ScalarExprPattern, TensorComputePattern, ReduceComputePattern
from hidet.utils.doc import Doc, NewLine, Text, doc_join
from hidet.utils.namer import Namer

from .base import StmtExprFunctor, TypeFunctor, WorkerFunctor


class IRPrinter(StmtExprFunctor, TypeFunctor, WorkerFunctor):
    def __init__(self):
        super().__init__()
        self.namer = Namer()

    def __call__(self, node):
        return self.visit(node)

    def visit(self, obj):
        if isinstance(obj, (list, tuple)):
            return doc_join([self(v) for v in obj], ', ')
        elif isinstance(obj, dict):
            return doc_join([self(k) + ': ' + self(v) for k, v in obj.items()], ', ')
        elif isinstance(obj, str):
            return Text(obj)
        elif isinstance(obj, (int, float)):
            return Text(str(obj))
        elif obj is None:
            return Text('None')
        elif isinstance(obj, TypeNode):
            return TypeFunctor.visit(self, obj)
        elif isinstance(obj, Function):
            return self.visit_Function(obj)
        elif isinstance(obj, IRModule):
            return self.visit_IRModule(obj)
        elif isinstance(obj, (Expr, Stmt)):
            return StmtExprFunctor.visit(self, obj)
        elif isinstance(obj, Worker):
            return WorkerFunctor.visit(self, obj)
        else:
            return object.__repr__(obj)

    def visit_Function(self, func: Function):
        self.namer.clear()
        doc = Doc()

        # parameters
        doc += 'fn('
        param_docs = []
        for i in range(len(func.params)):
            param = func.params[i]
            param_docs.append([NewLine(), self(param), ': ', self(param.type)])
        doc += doc_join(param_docs, Text(', '))
        doc += ')'
        doc = doc.indent(6)

        # locals
        for local_var in func.local_vars:
            doc += (NewLine() + Text('declare ') + self(local_var) + Text(': ') + self(local_var.type)).indent(4)

        # body
        doc += self(func.body).indent(4)

        return doc

    def visit_IRModule(self, ir_module: IRModule):
        doc = Doc()
        for name, func in ir_module.functions.items():
            doc += ['def ', name, ' ', self(func), NewLine(), NewLine()]
        return doc

    def visit_Add(self, e: Add):
        return Text('(') + self(e.a) + ' + ' + self(e.b) + ')'

    def visit_Sub(self, e: Sub):
        return Text('(') + self(e.a) + ' - ' + self(e.b) + ')'

    def visit_Multiply(self, e: Multiply):
        return Text('(') + self(e.a) + ' * ' + self(e.b) + ')'

    def visit_Div(self, e: Div):
        return Text('(') + self(e.a) + ' / ' + self(e.b) + ')'

    def visit_Mod(self, e: Mod):
        return Text('(') + self(e.a) + ' % ' + self(e.b) + ')'

    def visit_FloorDiv(self, e: FloorDiv):
        return Text('(') + self(e.a) + ' / ' + self(e.b) + ')'

    def visit_LessThan(self, e: LessThan):
        return Text('(') + self(e.a) + ' < ' + self(e.b) + ')'

    def visit_LessEqual(self, e: LessThan):
        return Text('(') + self(e.a) + ' <= ' + self(e.b) + ')'

    def visit_Equal(self, e: Equal):
        return Text('(') + self(e.a) + ' == ' + self(e.b) + ')'

    def visit_And(self, e: And):
        return Text('(') + self(e.a) + ' && ' + self(e.b) + ')'

    def visit_Or(self, e: Or):
        return Text('(') + self(e.a) + ' || ' + self(e.b) + ')'

    def visit_Not(self, e: Not):
        return Text('!') + self(e.a)

    def visit_TensorElement(self, e: TensorElement):
        return self(e.base) + '[' + self(e.indices) + ']'

    def visit_IfThenElse(self, e: IfThenElse):
        return '(' + self(e.cond) + ' ? ' + self(e.then_expr) + ' : ' + self(e.else_expr) + ')'

    def visit_Call(self, e: Call):
        return Text(e.func_var.hint) + '(' + self(e.args) + ')'

    def visit_Let(self, e: Let):
        return Text('let(') + self(e.var) + '=' + self(e.value) + ': ' + self(e.body) + ')'

    def visit_Cast(self, e: Cast):
        return Text('cast(') + self(e.target_type) + ', ' + self(e.expr) + ')'

    def visit_Reference(self, e: Reference):
        return Text('Ref(') + self(e.expr) + ')'

    def visit_Dereference(self, e: Dereference):
        return Text('*') + self(e.expr)

    def visit_Address(self, e: Address):
        return Text('&') + self(e.expr)

    def visit_Var(self, e: Var):
        return Text(self.namer.get_name(e))

    def visit_Constant(self, e: Constant):
        if e.value is None:
            return self('Constant(None, type=') + self(e.dtype) + ')'
        return Text(str(e.value))

    def visit_ScalarInput(self, e: ScalarInput):
        return self.namer.get_name(e)

    def visit_TensorInput(self, e: TensorInput):
        return self.namer.get_name(e)

    def visit_TensorCompute(self, e: TensorCompute):
        return self('TensorCompute(') + self(e.name) + ', ' + self(e.shape) + ', ' + self(e.value) + ')'

    def visit_ReduceCompute(self, e: ReduceCompute):
        return self('ReduceCompute(') + (self(e.name) + ', ' if e.name else '') + self(e.shape) + ', ' + self(e.axes) + ', ' + self(e.value) + ')'

    def visit_EvaluateStmt(self, stmt: EvaluateStmt):
        return NewLine() + self(stmt.expr)

    def visit_BufferStoreStmt(self, stmt: BufferStoreStmt):
        doc = NewLine()
        doc += self(stmt.buf)
        doc += '[' + self(stmt.indices) + ']'
        doc += ' = ' + self(stmt.value)
        return doc

    def visit_AssignStmt(self, stmt: AssignStmt):
        return NewLine() + self(stmt.var) + ' = ' + self(stmt.value)

    def visit_LetStmt(self, stmt: LetStmt):
        doc = NewLine() + 'let ' + self.visit(stmt.var) + ' = ' + self.visit(stmt.value) # + ' [' + str(id(stmt.value)) + ']'
        # doc += self.visit(stmt.body)
        doc += self.visit(stmt.body).indent()
        return doc

    def visit_SeqLetStmt(self, stmt: SeqLetStmt):
        doc = Doc()
        for bind_var, bind_value in zip(stmt.bind_vars, stmt.bind_values):
            doc += NewLine() + 'let ' + self(bind_var) + ' = ' + self(bind_value)
        # doc += self(stmt.body)
        doc += self(stmt.body).indent()
        return doc

    def visit_ForStmt(self, stmt: ForStmt):
        rng = Text('range(') + self(stmt.extent) + ')'
        doc = NewLine() + Text('for ') + self(stmt.loop_var) + ' in ' + rng
        if stmt.unroll is not None:
            if stmt.unroll:
                doc += '[unroll]'
            else:
                doc += '[no-unroll]'
        doc += self(stmt.body).indent(4)
        return doc

    def visit_IfStmt(self, stmt: IfStmt):
        doc = NewLine() + Text('if ') + self(stmt.cond)
        doc += self(stmt.then_body).indent(4)
        if stmt.else_body:
            doc += NewLine() + Text('else')
            doc += self(stmt.else_body).indent(4)
        return doc

    def visit_ReturnStmt(self, stmt: ReturnStmt):
        return NewLine() + Text('return')

    def visit_AssertStmt(self, stmt: AssertStmt):
        return NewLine() + 'assert(' + self(stmt.cond) + ', ' + stmt.msg + ')'

    def visit_AsmStmt(self, stmt: AsmStmt):
        volatile_doc = 'volatile ' if stmt.is_volatile else ''
        template_doc = Text(stmt.template_string)
        output_docs = []
        for label, expr in zip(stmt.output_labels, stmt.output_exprs):
            output_docs.append(Text(label) + '(' + self(expr) + ')')
        input_docs = []
        for label, expr in zip(stmt.input_labels, stmt.input_exprs):
            input_docs.append(Text(label) + '(' + self(expr) + ')')
        return NewLine() + 'asm ' + volatile_doc + '(' + template_doc + ' : ' + doc_join(input_docs, ', ') + ' : ' + doc_join(output_docs, ', ') + ');'

    def visit_BlackBoxStmt(self, stmt: BlackBoxStmt):
        expr_docs = [str(self(e)) for e in stmt.exprs]
        stmt_string: str = stmt.template_string.format(*expr_docs)
        lines = stmt_string.split('\n')
        doc = Text('')
        for line in lines:
            doc += NewLine() + line
        return doc

    def visit_SeqStmt(self, stmt: SeqStmt):
        doc = Doc()
        for idx, s in enumerate(stmt.seq):
            doc += self(s)
        return doc

    def visit_ScalarType(self, t: ScalarType):
        return Text('ScalarType({})'.format(t.name))

    def visit_TensorType(self, t: TensorType):
        return Text('TensorType(') + self(t.scalar_type) + ', [' + self(t.shape) + '], ' + t.scope.name + ')'

    def visit_PointerType(self, t: PointerType):
        return Text('PointerType(') + self(t.base_type) + ')'

    def visit_TensorPointerType(self, t: TensorPointerType):
        return Text('TensorPointerType(') + self(t.tensor_type) + ')'

    def visit_ReferenceType(self, t: ReferenceType):
        return Text('ReferenceType(') + self(t.base_type) + ')'

    def visit_VoidType(self, t: VoidType):
        return Text('VoidType')

    def visit_AnyExpr(self, e: AnyExpr):
        return Text('AnyExpr')

    def visit_ReduceComputePattern(self, e: ReduceComputePattern):
        return Text('ReduceComputePattern(allow_dynamic_axis=') + str(e.allow_dynamic_axis) + ')'

    def visit_TensorComputePattern(self, e: TensorComputePattern):
        return Text('TensorComputePattern(allow_dynamic_axis=') + str(e.allow_dynamic_axis) + ')'

    def visit_ScalarExprPattern(self, e: ScalarExprPattern):
        return Text('ScalarExprPattern(reduce=') + (self(e.reduce) if e.reduce else str(None)) + ')'

    def visit_Host(self, host: Host):
        return Text('Host')

    def visit_Grid(self, grid: Grid):
        grid_dim = self(grid.grid_dim) if grid.grid_dim else 'None'
        block_dim = self(grid.block_dim) if grid.block_dim else 'None'
        return Text('Grid(') + grid_dim + ', ' + block_dim + ')'

    def visit_ThreadBlock(self, block: ThreadBlock):
        block_dim = (self(block.block_dim) if block.block_dim else 'None')
        return Text('ThreadBlock(') + block_dim + ')'

    def visit_Warp(self, warp: Warp):
        return Text('Warp')

    def visit_Thread(self, thread: Thread):
        return Text('Thread')


def astext(obj: Node) -> str:
    if isinstance(obj, Node):
        printer = IRPrinter()
        return str(printer(obj))
    else:
        raise ValueError()

