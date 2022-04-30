from hidet.tos.ir import FlowGraph

from .base import GraphPass, PassContext
from .instruments import GraphPassInstrument, SaveGraphInstrument, ProfileInstrument
from .fold_const import fold_const_pass
from .pattern_transform import pattern_transform_pass
from .fuse_unary_elementwise import fuse_unary_elementwise_pass
from .fuse_epilogue import fuse_epilogue_pass
from .fuse_prologue import fuse_prologue_pass


def optimize(graph: FlowGraph) -> FlowGraph:
    passes = [
        fold_const_pass(),
        pattern_transform_pass(),
        fuse_unary_elementwise_pass(),
        fuse_epilogue_pass(),
        fuse_prologue_pass()
    ]
    ctx = PassContext.current()
    for inst in ctx.instruments:
        inst.before_all_passes(graph)
    for p in passes:
        graph = p(graph)
    for inst in reversed(ctx.instruments):
        inst.after_all_passes(graph)
    return graph.update_nodes()
