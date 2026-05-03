from abc import ABC, abstractmethod


class ResourceEstimator(ABC):
    """Base class for resource estimators."""

    @abstractmethod
    def create_visitor(self):
        """Create a visitor that computes this resource during traversal."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this resource type."""


class LoweringEngine:
    """Recursively lowers an Operation tree to primitives and computes resource costs."""

    def estimate(self, operation, estimator):
        visitor = estimator.create_visitor()
        operation.traverse(visitor)
        return visitor.get_result()


class TCountEstimator(ResourceEstimator):
    def create_visitor(self):
        from .visitor import TCounter
        return TCounter()

    @property
    def name(self):
        return "T-count"


class TDepthEstimator(ResourceEstimator):
    def create_visitor(self):
        from .visitor import TDepthCounter
        return TDepthCounter()

    @property
    def name(self):
        return "T-depth"


class SimulationEstimator(ResourceEstimator):
    def __init__(self, verbose=False):
        self._verbose = verbose

    def create_visitor(self):
        from .simulator import SimulatorVisitor
        return SimulatorVisitor(verbose=self._verbose)

    @property
    def name(self):
        return "simulation"


class ToffoliCountEstimator(ResourceEstimator):
    def create_visitor(self):
        from .visitor import ToffoliCounter
        return ToffoliCounter()

    @property
    def name(self):
        return "Toffoli-count"


class QECEstimator(ResourceEstimator):
    """Estimator that lowers to QEC-compiler AbstractCircuit."""
    def create_visitor(self):
        from .qec_lowering import QECLoweringVisitor
        return QECLoweringVisitor()

    @property
    def name(self):
        return "qec-compilation"


def to_abstract_circuit(operation):
    """Lower a pyqres Operation tree to a QEC AbstractCircuit.

    Requires qec-compiler to be installed.
    """
    from .qec_lowering import QECLoweringVisitor
    visitor = QECLoweringVisitor()
    return visitor.build_circuit(operation)


from .visitor import TCounter, TDepthCounter, ToffoliCounter
from .simulator import SimulatorVisitor

TCounter.get_result = TCounter.get_count
TDepthCounter.get_result = TDepthCounter.get_depth
ToffoliCounter.get_result = ToffoliCounter.get_count
SimulatorVisitor.get_result = lambda self: self.state
