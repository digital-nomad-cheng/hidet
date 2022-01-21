from itertools import product
from typing import Mapping

from hidet.implement.implementer import Implementer, register_impl
from hidet.ir.builders import FunctionBuilder, StmtBuilder
from hidet.ir.dialects.compute import TensorInput, TensorCompute
from hidet.ir.dialects.pattern import TaskPattern
from hidet.ir.expr import Constant, TensorElement, var, tensor_var
from hidet.ir.func import IRModule
from hidet.ir.node import Node
from hidet.ir.stmt import BufferStoreStmt, LetStmt
from hidet.ir.task import Task, Warp
from hidet.ir.type import scalar_type, TensorType, ScalarType, RegisterScope
from hidet.ir.primitives import thread_idx


@register_impl('cuda_warp_transfer_s2r_implementer')
class CudaWarpTransferS2RImplementer(Implementer):
    def __init__(self):
        self.shape = [Constant(None, dtype=scalar_type('int32')), Constant(None, dtype=scalar_type('int32'))]
        self.in_strides = [Constant(None, dtype=scalar_type('int32')), Constant(None, dtype=scalar_type('int32'))]

        self.input = TensorInput('in', None, None)
        self.axes = [var('i'), var('j')]
        self.value = TensorElement(self.input, self.axes)
        self.computation = TensorCompute('out',
                                         shape=self.shape,
                                         axes=self.axes,
                                         value=self.value
                                         )
        self.smem_dtype = ScalarType(None)
        self.regs_dtype = ScalarType(None)
        self.register_scope = RegisterScope()
        self.input_type = TensorType('shared', self.smem_dtype, None, self.in_strides)
        self.output_type = TensorType(self.register_scope, self.regs_dtype, None)

        self.pattern = TaskPattern(
            compute_pattern=self.computation,
            required_params=[self.input, self.computation],
            required_param_types=[self.input_type, self.output_type],
            allow_tensor_extra_params=False,
            worker=Warp()
        )

    def priority(self) -> int:
        return 0

    def task_pattern(self) -> TaskPattern:
        return self.pattern

    def implement(self, task: Task, match: Mapping[Node, Node]) -> IRModule:
        ir_module = IRModule()

        shape = [match[v] for v in self.shape]
        reg_scope: RegisterScope = match[self.register_scope]
        with FunctionBuilder(task.name, attrs={'worker': Warp()}) as fb:
            # params
            smem = tensor_var('smem', shape=shape, scope='shared', dtype=match[self.smem_dtype])
            regs = tensor_var('regs', shape=reg_scope.local_shape, scope=reg_scope, dtype=match[self.regs_dtype])
            fb.extend_params([smem, regs])
            # body
            sb = StmtBuilder()
            lain_id = var('lane_id')
            block_tid = thread_idx()
            sb.append(LetStmt(lain_id, block_tid % 32))
            sb.enter_body()
            local_m, local_n = reg_scope.local_shape
            for regs_locals in product(range(local_m), range(local_n)):
                regs_globals = reg_scope.local2global(lain_id, *regs_locals)
                sb.append(BufferStoreStmt(regs, regs_locals, TensorElement(smem, regs_globals)))
            sb.exit_body()
            fb.set_body(sb.finish())
        func = fb.get()
        ir_module.add(func.name, func)
        return ir_module

