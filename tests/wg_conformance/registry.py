"""W3C OWL WG conformance test registry.

Faithful Python port of the upstream Java harness:

  * ``org.semanticweb.HermiT.owl_wg_tests.WGTestRegistry`` -- loads ``all.rdf``
    and collects every ``test:TestCase`` individual.
  * ``org.semanticweb.HermiT.owl_wg_tests.WGTestDescriptor`` -- reads each test
    case's ``identifier``, ``status``, test ``types``, ``species``,
    ``semantics`` and the embedded premise / (non)conclusion ontology strings.
  * ``org.semanticweb.HermiT.owl_wg_tests.TstDescriptorForMaven`` -- the maven /
    quick parametrisation that keeps APPROVED || PROPOSED DL tests.

The upstream loads ``all.rdf`` through the OWL API. Here we parse it directly
with ``xml.etree`` because the file is a plain RDF/XML document whose test
metadata uses a fixed, flat vocabulary -- the same data the OWL API exposes,
without pulling a full RDF stack into the test suite. The discovered set is
asserted (in ``test_wg_conformance.py``) to match the counts the Java harness
generates so the parse stays faithful.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

URI_BASE = "http://www.w3.org/2007/OWL/testOntology#"
TEST_ID_PREFIX = "http://owl.semanticweb.org/id/"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
OWL = "http://www.w3.org/2002/07/owl#"

# The W3C OWL WG test data (all.rdf + owl:imports targets), vendored from the
# upstream HermiT test suite.
_ONTOLOGIES = Path(__file__).resolve().parent / "ontologies"
ALL_RDF = _ONTOLOGIES / "all.rdf"

# Mirrors AbstractTest.registerImportedReosurces(): the WG suite ships local
# copies of the ontologies that test premises import via owl:imports, and the
# Java harness maps those ontology IRIs onto the local files. consistent001
# and consistent002 import each other, so resolution must track visited IRIs.
IMPORT_MAP: dict[str, Path] = {
    "http://www.w3.org/2002/03owlt/miscellaneous/consistent001": _ONTOLOGIES
    / "consistent001.rdf",
    "http://www.w3.org/2002/03owlt/miscellaneous/consistent002": _ONTOLOGIES
    / "consistent002.rdf",
    "http://www.w3.org/2002/03owlt/imports/support011-A": _ONTOLOGIES
    / "support011-A.rdf",
}


class Status(str, Enum):
    APPROVED = "Approved"
    REJECTED = "Rejected"
    PROPOSED = "Proposed"
    EXTRACREDIT = "Extracredit"


class TestType(str, Enum):
    CONSISTENCY = "ConsistencyTest"
    INCONSISTENCY = "InconsistencyTest"
    POSITIVE_ENTAILMENT = "PositiveEntailmentTest"
    NEGATIVE_ENTAILMENT = "NegativeEntailmentTest"
    PROFILE_IDENTIFICATION = "ProfileIdentificationTest"


# data-property local names for each serialization format. The Java
# SerializationFormat enum iterates FUNCTIONAL, OWLXML, RDFXML and the OWL API
# parses all three; the embedded ontologies are logically identical across
# serializations. pyhermit's parser is owlready2-backed and reads RDF/XML, so
# we prefer RDFXML when present (same ontology) and fall back otherwise.
_FORMATS = [
    ("RDFXML", "rdfXmlPremiseOntology", "rdfXmlConclusionOntology", "rdfXmlNonConclusionOntology"),
    ("OWLXML", "owlXmlPremiseOntology", "owlXmlConclusionOntology", "owlXmlNonConclusionOntology"),
    ("FUNCTIONAL", "fsPremiseOntology", "fsConclusionOntology", "fsNonConclusionOntology"),
]

# file extension used when writing the embedded string to a temp file so the
# pyhermit parser (owlready2) picks the right syntax.
_FORMAT_EXT = {"FUNCTIONAL": ".ofn", "OWLXML": ".owx", "RDFXML": ".rdf"}


@dataclass
class WGTestDescriptor:
    identifier: str
    test_id: str
    status: Status | None
    test_types: set[TestType]
    species: set[str]
    semantics: set[str]
    # raw embedded ontology strings, keyed by local data-property name
    data_props: dict[str, str] = field(default_factory=dict)

    def is_dl_test(self) -> bool:
        # mirrors WGTestDescriptor.isDLTest()
        return "DIRECT" in self.semantics and "DL" in self.species

    def _string_for(self, names: list[str]) -> tuple[str, str] | None:
        """Return (format_name, ontology_string) using SerializationFormat order."""
        for fmt, _premise, _concl, _nonconcl in _FORMATS:
            idx = {"premise": _premise, "conclusion": _concl, "nonconclusion": _nonconcl}
            # names is one of those role keys
            key = idx[names[0]]
            if key in self.data_props:
                return fmt, self.data_props[key]
        return None

    def premise_string(self) -> tuple[str, str] | None:
        return self._string_for(["premise"])

    def conclusion_string(self, positive: bool) -> tuple[str, str] | None:
        return self._string_for(["conclusion" if positive else "nonconclusion"])


def _local(uri: str | None) -> str | None:
    if uri is None:
        return None
    if "#" in uri:
        return uri.rsplit("#", 1)[1]
    return uri.rsplit("/", 1)[-1]


def load_descriptors() -> list[WGTestDescriptor]:
    """Parse all.rdf into descriptors (faithful to WGTestRegistry)."""
    tree = ET.parse(ALL_RDF)
    root = tree.getroot()
    descriptors: list[WGTestDescriptor] = []
    for tc in root.findall(f"{{{URI_BASE}}}TestCase"):
        about = tc.get(f"{{{RDF}}}about")
        if about is None or not about.startswith(TEST_ID_PREFIX):
            continue
        test_id = about[len(TEST_ID_PREFIX):]

        identifier = None
        status: Status | None = None
        types: set[TestType] = set()
        species: set[str] = set()
        semantics: set[str] = set()
        data_props: dict[str, str] = {}

        for child in tc:
            tag = child.tag
            if not tag.startswith(f"{{{URI_BASE}}}") and not tag.startswith(f"{{{RDF}}}"):
                continue
            local = tag.split("}", 1)[1]
            resource = child.get(f"{{{RDF}}}resource")
            if tag == f"{{{RDF}}}type":
                tt = _local(resource)
                for t in TestType:
                    if t.value == tt:
                        types.add(t)
            elif local == "identifier":
                identifier = (child.text or "").strip()
            elif local == "status":
                st = _local(resource)
                for s in Status:
                    if s.value == st:
                        status = s
            elif local == "species":
                species.add(_local(resource) or "")
            elif local == "semantics":
                semantics.add(_local(resource) or "")
            elif local.endswith("PremiseOntology") or local.endswith(
                "ConclusionOntology"
            ):
                data_props[local] = child.text or ""

        if identifier is None:
            raise ValueError(f"Test {test_id} has no identifier")
        descriptors.append(
            WGTestDescriptor(
                identifier=identifier,
                test_id=test_id,
                status=status,
                test_types=types,
                species=species,
                semantics=semantics,
                data_props=data_props,
            )
        )
    return descriptors


@dataclass
class Subtest:
    descriptor: WGTestDescriptor
    test_type: TestType
    positive: bool
    use_disjunction_learning: bool

    @property
    def name(self) -> str:
        suffix = {
            TestType.CONSISTENCY: "-consistency",
            TestType.INCONSISTENCY: "-inconsistency",
            TestType.POSITIVE_ENTAILMENT: "-entailment",
            TestType.NEGATIVE_ENTAILMENT: "-nonentailment",
        }[self.test_type]
        return self.descriptor.identifier + suffix


def _disjunction_learning(identifier: str) -> bool:
    # mirrors TstDescriptorForMaven
    return not (
        identifier.startswith("WebOnt-description-logic-209")
        or identifier.startswith("WebOnt-description-logic-208")
    )


def generate_subtests(statuses: set[Status]) -> list[Subtest]:
    """Expand DL descriptors of the given statuses into per-type subtests.

    Mirrors WGTestDescriptor.getTest / TstDescriptorForMaven: PROFILE
    identification is skipped; each of CONSISTENCY, INCONSISTENCY,
    POSITIVE_ENTAILMENT, NEGATIVE_ENTAILMENT present on the case becomes one
    subtest.
    """
    subtests: list[Subtest] = []
    order = [
        (TestType.CONSISTENCY, True),
        (TestType.INCONSISTENCY, False),
        (TestType.POSITIVE_ENTAILMENT, True),
        (TestType.NEGATIVE_ENTAILMENT, False),
    ]
    for d in load_descriptors():
        if not d.is_dl_test():
            continue
        if d.status not in statuses:
            continue
        udl = _disjunction_learning(d.identifier)
        for tt, positive in order:
            if tt in d.test_types:
                subtests.append(Subtest(d, tt, positive, udl))
    return subtests


def format_extension(fmt: str) -> str:
    return _FORMAT_EXT[fmt]
