from typing import Mapping, Any

from hidet.implement import register_impl, Implementer
from hidet.ir import IRModule
from hidet.ir.dialects.pattern import TaskPattern
from hidet.ir.node import Node
from hidet.ir.task import Task


@register_impl('cuda_grid_static_conv2d_implicit_gemm_implementer')
class CudaGridStaticConv2dImplicitGemmImplementer(Implementer):
    def __init__(self):
        pass

    def priority(self) -> int:
        return 1

    def task_pattern(self) -> TaskPattern:
        pass

    def implement(self, task: Task, match: Mapping[Node, Any]) -> IRModule:
        pass

