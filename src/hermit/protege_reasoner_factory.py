"""Protege reasoner factory stub.

Ports ``org.semanticweb.HermiT.ProtegeReasonerFactory`` from the Java
HermiT reasoner.

This class is **not implemented** because Protege integration requires
the Java-based Protege desktop application and its OWL API plug-in
mechanism, which are out of scope for the Python port.

Attempting to instantiate this class raises ``NotImplementedError`` with
an explanation.
"""

from __future__ import annotations

__all__ = ["ProtegeReasonerFactory"]


class ProtegeReasonerFactory:
    """Stub for Protege desktop integration.

    The Java HermiT reasoner ships as a Protege plug-in via this factory
    class, which extends ``AbstractProtegeOWLReasonerInfo`` and reads
    Protege's ``ReasonerPreferences`` to selectively enable or disable
    inference tasks (class classification, realisation, property
    hierarchies, etc.).

    The Python port does not target the Protege desktop application.
    If you need to use HermiT from Protege, use the original Java
    distribution available at <https://hermit-reasoner.org/>.
    """

    def __init__(self) -> None:
        raise NotImplementedError(
            "ProtegeReasonerFactory is a stub.\n\n"
            "The HermiT Python port does not support Protege desktop "
            "integration because Protege is a Java application with a "
            "Java-only plug-in API (OWLReasonerFactory / "
            "AbstractProtegeOWLReasonerInfo).\n\n"
            "To use HermiT with Protege, install the original Java "
            "HermiT plug-in from https://hermit-reasoner.org/.\n\n"
            "For programmatic use of the Python port, create a Reasoner "
            "directly:\n\n"
            "    from hermit import Reasoner, Configuration\n"
            "    from hermit.model import DLOntology\n\n"
            "    ontology = ...  # build or load DLOntology\n"
            "    reasoner = Reasoner(ontology)\n"
            "    print(reasoner.is_consistent())\n"
        )
