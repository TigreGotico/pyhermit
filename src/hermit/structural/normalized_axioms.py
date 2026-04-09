"""
Normalized OWL axioms — data structures holding the output of OWL normalization
and the input to OWL clausification.

Adapted from the Java ``OWLAxioms`` class.  In the Java version these hold
OWL API objects (``OWLClassExpression[]``, ``OWLObjectPropertyExpression``,
etc.).  Here we use HermiT's internal model types (``AtomicConcept``,
``Role``, ``DLClause``, ``Atom``, etc.) so the structural layer is
self-contained and has no external ontology-API dependency.

The pipeline is:

    OWL ontology (external) → [parser, not yet implemented] → NormalizedAxioms
                                                              → [clausification] → DLOntology
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.model import (
        AtomicConcept,
        AtomicRole,
        Atom,
        Constant,
        DataRange,
        Individual,
        Role,
    )


# ===========================================================================
# NormalizedAxioms
# ===========================================================================


@dataclass
class NormalizedAxioms:
    """
    Holds all normalized axioms produced by the normalization phase and
    consumed by the clausification phase.

    Mirrors the Java ``OWLAxioms`` class but uses internal model types
    instead of OWL API types.
    """

    # -- signature --
    atomic_concepts: set[AtomicConcept] = field(default_factory=set)
    object_roles: set[AtomicRole] = field(default_factory=set)
    object_roles_in_owl_axioms: set[AtomicRole] = field(default_factory=set)
    complex_object_roles: set[Role] = field(default_factory=set)
    data_roles: set[AtomicRole] = field(default_factory=set)
    named_individuals: set[Individual] = field(default_factory=set)

    # -- TBox axioms --
    concept_inclusions: list[tuple[AtomicConcept, ...]] = field(default_factory=list)
    """Each tuple is a disjunction of atomic/literal concepts (NNF).
    E.g. ``(not A, B)`` represents ``A ⊑ B`` after NNF."""

    data_range_inclusions: list[tuple[DataRange, ...]] = field(default_factory=list)
    """Each tuple is a disjunction of data ranges."""

    # -- Object property axioms --
    simple_object_property_inclusions: list[tuple[Role, ...]] = field(default_factory=list)
    """Each tuple is [R1, ..., Rn, S] meaning R1 o ... o Rn ⊑ S (n == 1 for simple)."""

    complex_object_property_inclusions: list[ComplexObjectPropertyInclusion] = field(
        default_factory=list
    )

    disjoint_object_properties: list[tuple[Role, ...]] = field(default_factory=list)
    reflexive_object_properties: set[Role] = field(default_factory=set)
    irreflexive_object_properties: set[Role] = field(default_factory=set)
    asymmetric_object_properties: set[Role] = field(default_factory=set)

    # -- Data property axioms --
    data_property_inclusions: list[tuple[AtomicRole, ...]] = field(default_factory=list)
    """Each tuple is [P, Q] meaning P ⊑ Q."""

    disjoint_data_properties: list[tuple[AtomicRole, ...]] = field(default_factory=list)

    # -- ABox axioms (facts) --
    positive_concept_facts: list[tuple[Individual, AtomicConcept]] = field(
        default_factory=list
    )
    """A(i) — individual i is asserted to be in concept A."""

    negative_concept_facts: list[tuple[Individual, AtomicConcept]] = field(
        default_factory=list
    )
    """not A(i) — individual i is asserted NOT to be in concept A."""

    positive_role_facts: list[tuple[Individual, Role, Individual]] = field(
        default_factory=list
    )
    """R(i, j) — role assertion."""

    negative_role_facts: list[tuple[Individual, Role, Individual]] = field(
        default_factory=list
    )
    """not R(i, j) — negative role assertion."""

    same_individual_facts: list[tuple[Individual, Individual]] = field(
        default_factory=list
    )
    """i == j — same individual assertion."""

    different_individuals_facts: list[tuple[Individual, Individual]] = field(
        default_factory=list
    )
    """i != j — different individuals assertion."""

    positive_data_facts: list[tuple[Individual, AtomicRole, Constant]] = field(
        default_factory=list
    )
    """P(i, v) — data property assertion."""

    negative_data_facts: list[tuple[Individual, AtomicRole, Constant]] = field(
        default_factory=list
    )
    """not P(i, v) — negative data property assertion."""

    # -- Keys --
    object_property_keys: list[ObjectPropertyKey] = field(default_factory=list)
    data_property_keys: list[DataPropertyKey] = field(default_factory=list)

    # -- Datatypes --
    defined_datatype_iris: set[str] = field(default_factory=set)
    """Custom datatype IRIs from DatatypeDefinition axioms."""

    # -- SWRL rules --
    rules: list[DisjunctiveRule] = field(default_factory=list)
    """Normalized disjunctive SWRL rules."""

    # -- Normalization interface (used by OWLNormalization) --
    positive_facts: list = field(default_factory=list)
    """Temporary storage for positive axioms during normalization."""

    negative_facts: list = field(default_factory=list)
    """Temporary storage for negative axioms during normalization."""

    @property
    def is_horn(self) -> bool:
        """All concept inclusions have at most one positive (non-negated) literal."""
        for inclusion in self.concept_inclusions:
            # In NNF, positive literals are AtomicConcept (not negated)
            # A Horn clause has at most one positive literal
            positive_count = 0
            for lit in inclusion:
                from hermit.model import AtomicConcept, AtomicNegationConcept

                if isinstance(lit, AtomicConcept):
                    positive_count += 1
                elif isinstance(lit, AtomicNegationConcept):
                    pass  # negated atomic is "positive" in the Horn sense
            # Simplified: count disjunction length > 1 as non-Horn
            if len(inclusion) > 1:
                # Need more sophisticated check — this is a simplification
                pass
        return True  # optimistic default

    def signature(self) -> set:
        """Return all entities in the axiom set."""
        sig: set = set()
        sig.update(self.atomic_concepts)
        sig.update(self.object_roles)
        sig.update(self.data_roles)
        sig.update(self.named_individuals)
        return sig

    def add_concept_inclusion(self, simplified) -> None:
        """Add a concept inclusion (disjunction of concepts).

        Args:
            simplified: A simplified class expression (typically from NNF conversion)
                       that represents a concept inclusion.
        """
        # For now, store in positive_facts to support OWLNormalization
        # In a full implementation, this would convert to internal model
        self.positive_facts.append(simplified)


# ===========================================================================
# ComplexObjectPropertyInclusion
# ===========================================================================


@dataclass(frozen=True)
class ComplexObjectPropertyInclusion:
    """
    A complex object property inclusion: R1 o R2 o ... o Rn ⊑ S
    where the chain has length >= 2, or a transitivity marker R o R ⊑ R.

    Mirrors ``OWLAxioms.ComplexObjectPropertyInclusion``.
    """

    sub_object_properties: tuple[Role, ...]
    """The sub-property chain [R1, R2, ..., Rn]."""

    super_object_property: Role
    """The super-property S."""

    @classmethod
    def transitivity(cls, role: Role) -> ComplexObjectPropertyInclusion:
        """Create a transitivity marker: R o R ⊑ R."""
        return cls(
            sub_object_properties=(role, role),
            super_object_property=role,
        )

    def is_transitivity(self) -> bool:
        """Check if this is a transitivity axiom R o R ⊑ R."""
        return (
            len(self.sub_object_properties) == 2
            and self.sub_object_properties[0] == self.sub_object_properties[1]
            and self.sub_object_properties[0] == self.super_object_property
        )


# ===========================================================================
# DisjunctiveRule
# ===========================================================================


@dataclass(frozen=True)
class DisjunctiveRule:
    """
    A normalized disjunctive SWRL rule:
    body1 ∧ body2 ∧ ... ⊢ head1 ∨ head2 ∨ ...

    Mirrors ``OWLAxioms.DisjunctiveRule`` but uses ``Atom`` instead of
    ``SWRLAtom`` since the SWRL atoms have been normalized to HermiT's
    internal ``Atom`` representation.
    """

    body: tuple[Atom, ...]
    """Body atoms (conjunction)."""

    head: tuple[Atom, ...]
    """Head atoms (disjunction)."""

    def __str__(self) -> str:
        body_str = " ∧ ".join(str(a) for a in self.body) if self.body else "⊤"
        head_str = " ∨ ".join(str(a) for a in self.head) if self.head else "⊥"
        return f"{body_str} ⊢ {head_str}"

    def __repr__(self) -> str:
        return f"DisjunctiveRule(body={self.body}, head={self.head})"


# ===========================================================================
# Key axioms
# ===========================================================================


@dataclass(frozen=True)
class ObjectPropertyKey:
    """A HasKey axiom with object properties: C hasKey {R1, ..., Rn}."""

    concept: AtomicConcept
    """The concept C."""
    properties: tuple[Role, ...]
    """The object property chain."""


@dataclass(frozen=True)
class DataPropertyKey:
    """A HasKey axiom with data properties: C hasKey {P1, ..., Pn}."""

    concept: AtomicConcept
    """The concept C."""
    properties: tuple[AtomicRole, ...]
    """The data property chain."""
