"""Lazy public exports: scope checks do not import numerical dependencies."""
__all__=['WorldSession','OperationRequest']
def __getattr__(name):
    if name=='WorldSession':
        from .session import WorldSession
        return WorldSession
    if name=='OperationRequest':
        from .contracts import OperationRequest
        return OperationRequest
    raise AttributeError(name)
