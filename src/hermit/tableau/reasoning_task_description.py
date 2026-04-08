"""Describes a reasoning task for logging and monitoring purposes."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hermit.model import Concept, DLPredicate, Role, Term


class StandardTestType(Enum):
    """Standard categories of reasoning tasks."""

    CONCEPT_SATISFIABILITY = "satisfiability of concept '{0}'"
    CONSISTENCY = "ABox satisfiability"
    CONCEPT_SUBSUMPTION = "concept subsumption '{0}' => '{1}'"
    OBJECT_ROLE_SATISFIABILITY = "satisfiability of object role '{0}'"
    DATA_ROLE_SATISFIABILITY = "satisfiability of data role '{0}'"
    OBJECT_ROLE_SUBSUMPTION = "object role subsumption '{0}' => '{1}'"
    DATA_ROLE_SUBSUMPTION = "data role subsumption '{0}' => '{1}'"
    INSTANCE_OF = "class instance '{0}'('{1}')"
    OBJECT_ROLE_INSTANCE_OF = "object role instance '{0}'('{1}', '{2}')"
    DATA_ROLE_INSTANCE_OF = "data role instance '{0}'('{1}', '{2}')"
    ENTAILMENT = "entailment of '{0}'"
    DOMAIN = "check if {0} is domain of {1}"
    RANGE = "check if {0} is range of {1}"


class ReasoningTaskDescription:
    """Human-readable description of a reasoning task.

    Args:
        flip_satisfiability_result: Whether to flip the satisfiability result.
        test_type: The standard test type (or a custom ``message_pattern``).
        *arguments: Formatting arguments substituted into the message pattern.
    """

    __slots__ = ("_flip_satisfiability_result", "_message_pattern", "_arguments")

    def __init__(
        self,
        flip_satisfiability_result: bool,
        test_type: StandardTestType | str,
        *arguments: Any,
    ) -> None:
        if isinstance(test_type, StandardTestType):
            message_pattern = test_type.value
        else:
            message_pattern = test_type
        self._flip_satisfiability_result = flip_satisfiability_result
        self._message_pattern = message_pattern
        self._arguments: tuple[Any, ...] = arguments

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def flip_satisfiability_result(self) -> bool:
        """Whether the satisfiability result should be negated."""
        return self._flip_satisfiability_result

    @property
    def message_pattern(self) -> str:
        """The raw message pattern string (with ``{0}``, ``{1}``, … placeholders)."""
        return self._message_pattern

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def get_task_description(self, prefixes: Any) -> str:
        """Return the formatted task description with *prefixes* applied.

        Args:
            prefixes: A ``Prefixes``-like object used to convert model objects
                to their string representation.
        """
        result = self._message_pattern
        for idx, argument in enumerate(self._arguments):
            argument_string = _to_string_with_prefixes(argument, prefixes)
            result = result.replace("{" + str(idx) + "}", argument_string)
        return result

    def __str__(self) -> str:
        from hermit.model import Prefixes

        return self.get_task_description(Prefixes())

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def is_a_box_satisfiable(cls) -> ReasoningTaskDescription:
        return cls(False, StandardTestType.CONSISTENCY)

    @classmethod
    def is_concept_satisfiable(cls, atomic_concept: Any) -> ReasoningTaskDescription:
        return cls(False, StandardTestType.CONCEPT_SATISFIABILITY, atomic_concept)

    @classmethod
    def is_concept_subsumed_by(
        cls, atomic_subconcept: Any, atomic_superconcept: Any
    ) -> ReasoningTaskDescription:
        return cls(
            True,
            StandardTestType.CONCEPT_SUBSUMPTION,
            atomic_subconcept,
            atomic_superconcept,
        )

    @classmethod
    def is_concept_subsumed_by_list(
        cls, atomic_subconcept: Any, *atomic_superconcepts: Any
    ) -> ReasoningTaskDescription:
        parts = ["satisiability of concept '{0}'"]
        for idx in range(len(atomic_superconcepts)):
            parts.append(f" and not({{{idx + 1}}})")
        message = "".join(parts)
        arguments: list[Any] = [atomic_subconcept, *atomic_superconcepts]
        return cls(False, message, *arguments)

    @classmethod
    def is_role_subsumed_by_list(
        cls, subrole: Any, *superroles: Any
    ) -> ReasoningTaskDescription:
        parts = ["satisiability of role '{0}'"]
        for idx in range(len(superroles)):
            parts.append(f" and not({{{idx + 1}}})")
        message = "".join(parts)
        arguments: list[Any] = [subrole, *superroles]
        return cls(False, message, *arguments)

    @classmethod
    def is_role_satisfiable(
        cls, role: Any, is_object_role: bool
    ) -> ReasoningTaskDescription:
        test_type = (
            StandardTestType.OBJECT_ROLE_SATISFIABILITY
            if is_object_role
            else StandardTestType.DATA_ROLE_SATISFIABILITY
        )
        return cls(False, test_type, role)

    @classmethod
    def is_role_subsumed_by(
        cls, subrole: Any, superrole: Any, is_object_role: bool
    ) -> ReasoningTaskDescription:
        test_type = (
            StandardTestType.OBJECT_ROLE_SUBSUMPTION
            if is_object_role
            else StandardTestType.DATA_ROLE_SUBSUMPTION
        )
        return cls(True, test_type, subrole, superrole)

    @classmethod
    def is_instance_of(
        cls, atomic_concept: Any, individual: Any
    ) -> ReasoningTaskDescription:
        return cls(True, StandardTestType.INSTANCE_OF, atomic_concept, individual)

    @classmethod
    def is_object_role_instance_of(
        cls, atomic_role: Any, individual1: Any, individual2: Any
    ) -> ReasoningTaskDescription:
        return cls(
            True,
            StandardTestType.OBJECT_ROLE_INSTANCE_OF,
            atomic_role,
            individual1,
            individual2,
        )

    @classmethod
    def is_data_role_instance_of(
        cls, atomic_role: Any, individual1: Any, individual2: Any
    ) -> ReasoningTaskDescription:
        return cls(
            True,
            StandardTestType.DATA_ROLE_INSTANCE_OF,
            atomic_role,
            individual1,
            individual2,
        )

    @classmethod
    def is_axiom_entailed(cls, axiom: Any) -> ReasoningTaskDescription:
        return cls(True, StandardTestType.ENTAILMENT, axiom)

    @classmethod
    def is_domain_of(cls, domain: Any, role: Any) -> ReasoningTaskDescription:
        return cls(True, StandardTestType.DOMAIN, domain, role)

    @classmethod
    def is_range_of(cls, range_: Any, role: Any) -> ReasoningTaskDescription:
        return cls(True, StandardTestType.RANGE, range_, role)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _to_string_with_prefixes(obj: Any, prefixes: Any) -> str:
    """Convert *obj* to a string using *prefixes* if applicable."""
    if isinstance(obj, DLPredicate):
        return obj.to_string(prefixes)  # type: ignore[attr-defined]
    if isinstance(obj, Role):
        return obj.to_string(prefixes)  # type: ignore[attr-defined]
    if isinstance(obj, Concept):
        return obj.to_string(prefixes)  # type: ignore[attr-defined]
    if isinstance(obj, Term):
        return obj.to_string(prefixes)  # type: ignore[attr-defined]
    return str(obj)
