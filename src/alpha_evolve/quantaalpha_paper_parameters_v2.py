"""Explicit paper-parameter wiring around pinned, unmodified QuantaAlpha source."""

import hashlib


def install_round_boundary(controller_class, events):
    """Guard recursive phase transitions BEFORE they can make another LLM call."""
    for name in ["_get_original_task", "_get_mutation_task", "_get_crossover_task"]:
        original = getattr(controller_class, name)

        def guarded(self, *args, _original=original, _name=name, **kwargs):
            if self._current_round >= self.config.max_rounds:
                events.append(
                    {"phase_method": _name, "round": self._current_round, "round_limit": self.config.max_rounds}
                )
                return None
            return _original(self, *args, **kwargs)

        setattr(controller_class, name, guarded)


def install_paper_parameters():
    from quantaalpha.factors.coder.config import FACTOR_COSTEER_SETTINGS
    from quantaalpha.factors import proposal
    from quantaalpha.pipeline.evolution.controller import EvolutionController

    # The YAML factor section is not consumed by the released constructor.
    FACTOR_COSTEER_SETTINGS.symbol_length_threshold = 250
    FACTOR_COSTEER_SETTINGS.base_features_threshold = 6
    FACTOR_COSTEER_SETTINGS.duplication_threshold = 5
    native_init = proposal.AlphaAgentHypothesis2FactorExpression.__init__

    def init(self, *args, **kwargs):
        native_init(self, *args, **kwargs)
        self.factor_regulator.symbol_length_threshold = 250
        self.factor_regulator.base_features_threshold = 6
        self.factor_regulator.duplication_threshold = 5

    proposal.AlphaAgentHypothesis2FactorExpression.__init__ = init
    changes = []

    def rewrite(value, path=""):
        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(child, str) and "Ensure each generation produces 2-3 factors." in child:
                    updated = child.replace(
                        "Ensure each generation produces 2-3 factors.",
                        "Ensure each generation attempts to produce 3 factors.",
                    )
                    value[key] = updated
                    changes.append(
                        {
                            "path": path + "/" + key,
                            "before_sha256": hashlib.sha256(child.encode()).hexdigest(),
                            "after_sha256": hashlib.sha256(updated.encode()).hexdigest(),
                        }
                    )
                else:
                    rewrite(child, path + "/" + str(key))

    rewrite(proposal.qa_prompt_dict)
    if len(changes) != 1:
        raise ValueError("Expected exactly one source factor-cardinality prompt clause")
    events = []
    install_round_boundary(EvolutionController, events)
    return {
        "prompt_edits": changes,
        "round_boundary_events": events,
        "constructor_limits": {"symbol_length": 250, "base_features": 6, "duplication": 5},
        "native_file_edits": 0,
        "reference_zoo_reconstructed": False,
    }
