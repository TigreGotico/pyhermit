"""Integration tests loading real OWL ontologies from tests/ontologies/.

Tests exercise the full pipeline:
  OWL file → load_ontology() → OWLNormalization → OWLClausification → Reasoner

Pizza ontology is the standard example ontology for OWL reasoners.
Koala ontology is another standard example.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ONTOLOGIES_DIR = Path(__file__).parent / "ontologies"
PIZZA_OWL = ONTOLOGIES_DIR / "pizza.owl"
KOALA_OWL = ONTOLOGIES_DIR / "koala.owl"


def _has_owlready2() -> bool:
    try:
        import owlready2  # noqa: F401
        return True
    except ImportError:
        return False


requires_owlready2 = pytest.mark.skipif(
    not _has_owlready2(), reason="owlready2 not installed"
)


def _reasoner_from_file(path: Path):  # type: ignore[no-untyped-def]
    from hermit import Reasoner
    from hermit.parser import load_ontology
    from hermit.structural.owl_normalization import OWLNormalization
    from hermit.structural.owl_clausification import OWLClausification

    axioms = load_ontology(path)
    norm = OWLNormalization()
    normalized = norm.process_ontology(axioms)
    claus = OWLClausification()
    dl_onto = claus.clausify(normalized, ontology_iri=f"urn:test:{path.stem}")
    return Reasoner(dl_onto)


# ---------------------------------------------------------------------------
# Pizza ontology tests
# ---------------------------------------------------------------------------

@requires_owlready2
@pytest.mark.skipif(not PIZZA_OWL.exists(), reason="pizza.owl not found")
class TestPizzaOntology:
    def test_pizza_loads(self) -> None:
        """Loading pizza.owl returns at least one axiom."""
        from hermit.parser import load_ontology
        axioms = load_ontology(PIZZA_OWL)
        assert len(axioms) > 0

    def test_pizza_is_consistent(self) -> None:
        """Pizza ontology is consistent."""
        r = _reasoner_from_file(PIZZA_OWL)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_pizza_axiom_count(self) -> None:
        """Pizza ontology has a reasonable number of axioms."""
        from hermit.parser import load_ontology
        axioms = load_ontology(PIZZA_OWL)
        # The test pizza.owl is a subset — should have at least a handful
        assert len(axioms) >= 5

    def test_pizza_class_hierarchy(self) -> None:
        """CheeseTopping is a subclass of PizzaTopping in the pizza ontology."""
        from hermit.model import AtomicConcept
        r = _reasoner_from_file(PIZZA_OWL)
        try:
            ns = "http://www.co-ode.org/ontologies/pizza/pizza.owl#"
            cheese = AtomicConcept.create(ns + "CheeseTopping")
            topping = AtomicConcept.create(ns + "PizzaTopping")
            # CheeseTopping ⊑ PizzaTopping is stated directly
            assert r.is_sub_class_of(cheese, topping) is True
        finally:
            r.dispose()

    def test_pizza_meat_is_topping(self) -> None:
        """MeatTopping is a subclass of PizzaTopping."""
        from hermit.model import AtomicConcept
        r = _reasoner_from_file(PIZZA_OWL)
        try:
            ns = "http://www.co-ode.org/ontologies/pizza/pizza.owl#"
            meat = AtomicConcept.create(ns + "MeatTopping")
            topping = AtomicConcept.create(ns + "PizzaTopping")
            assert r.is_sub_class_of(meat, topping) is True
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# Koala ontology tests
# ---------------------------------------------------------------------------

@requires_owlready2
@pytest.mark.skipif(not KOALA_OWL.exists(), reason="koala.owl not found")
class TestKoalaOntology:
    def test_koala_loads(self) -> None:
        """Loading koala.owl returns at least one axiom."""
        from hermit.parser import load_ontology
        axioms = load_ontology(KOALA_OWL)
        assert len(axioms) > 0

    def test_koala_is_consistent(self) -> None:
        """Koala ontology is consistent."""
        r = _reasoner_from_file(KOALA_OWL)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()
