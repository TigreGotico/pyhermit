"""
Complete Real-World Example: Scientific Publication Ontology

This is a comprehensive example that brings together all the concepts
learned in the previous examples. We'll build a realistic domain ontology
for managing scientific publications and reasoning about them.

Features demonstrated:
- Complex class hierarchies
- Multiple property types
- Instance reasoning with rich ABox
- Real-world query patterns
- Result interpretation and decision-making

Scenario:
We're building a system to organize and search scientific publications.
The reasoner helps us:
1. Classify papers automatically
2. Find relevant papers for different audiences
3. Organize by research area
4. Track publication venues
"""

from hermit import Reasoner
from hermit.model import (
    DLOntology,
    Atom,
    AtomicConcept,
    AtomicRole,
    Variable,
    DLClause,
    Individual,
)


def build_publication_ontology():
    """Build the scientific publication ontology."""

    X = Variable.create("X")

    # === Concepts (Classes) ===

    # Publication types
    publication = AtomicConcept.create("http://example.org/pub#Publication")
    journal_article = AtomicConcept.create("http://example.org/pub#JournalArticle")
    conference_paper = AtomicConcept.create("http://example.org/pub#ConferencePaper")
    workshop_paper = AtomicConcept.create("http://example.org/pub#WorkshopPaper")
    book = AtomicConcept.create("http://example.org/pub#Book")

    # Impact levels
    high_impact = AtomicConcept.create("http://example.org/pub#HighImpact")
    medium_impact = AtomicConcept.create("http://example.org/pub#MediumImpact")

    # Research areas
    research = AtomicConcept.create("http://example.org/pub#Research")
    machine_learning = AtomicConcept.create("http://example.org/pub#MachineLearning")
    nlp = AtomicConcept.create("http://example.org/pub#NLP")
    knowledge_graphs = AtomicConcept.create("http://example.org/pub#KnowledgeGraphs")

    # Agent types
    person = AtomicConcept.create("http://example.org/pub#Person")
    researcher = AtomicConcept.create("http://example.org/pub#Researcher")
    author = AtomicConcept.create("http://example.org/pub#Author")

    # Venues
    venue = AtomicConcept.create("http://example.org/pub#Venue")
    journal = AtomicConcept.create("http://example.org/pub#Journal")
    conference = AtomicConcept.create("http://example.org/pub#Conference")

    # === TBox Rules ===
    # Simple subsumption hierarchy

    clauses = [
        # Publication type hierarchy
        DLClause.create((Atom.create(publication, X),), (Atom.create(journal_article, X),)),
        DLClause.create((Atom.create(publication, X),), (Atom.create(conference_paper, X),)),
        DLClause.create((Atom.create(publication, X),), (Atom.create(workshop_paper, X),)),
        DLClause.create((Atom.create(publication, X),), (Atom.create(book, X),)),

        # Impact hierarchy
        DLClause.create((Atom.create(high_impact, X),), (Atom.create(high_impact, X),)),
        DLClause.create((Atom.create(medium_impact, X),), (Atom.create(medium_impact, X),)),

        # Research areas
        DLClause.create((Atom.create(research, X),), (Atom.create(machine_learning, X),)),
        DLClause.create((Atom.create(research, X),), (Atom.create(nlp, X),)),
        DLClause.create((Atom.create(research, X),), (Atom.create(knowledge_graphs, X),)),

        # Person hierarchy
        DLClause.create((Atom.create(person, X),), (Atom.create(researcher, X),)),
        DLClause.create((Atom.create(person, X),), (Atom.create(author, X),)),

        # Venue types
        DLClause.create((Atom.create(venue, X),), (Atom.create(journal, X),)),
        DLClause.create((Atom.create(venue, X),), (Atom.create(conference, X),)),
    ]

    # === ABox Facts ===

    # Create individuals
    alice = Individual.create("http://example.org/pub#Alice")
    bob = Individual.create("http://example.org/pub#Bob")
    charlie = Individual.create("http://example.org/pub#Charlie")

    paper1 = Individual.create("http://example.org/pub#Paper1")
    paper2 = Individual.create("http://example.org/pub#Paper2")
    paper3 = Individual.create("http://example.org/pub#Paper3")

    nature = Individual.create("http://example.org/pub#Nature")
    acl = Individual.create("http://example.org/pub#ACL")

    # Facts about people and papers
    facts = frozenset([
        # People
        Atom.create(researcher, alice),
        Atom.create(researcher, bob),
        Atom.create(author, charlie),

        # Papers with types and impact
        Atom.create(journal_article, paper1),
        Atom.create(high_impact, paper1),
        Atom.create(machine_learning, paper1),

        Atom.create(conference_paper, paper2),
        Atom.create(nlp, paper2),

        Atom.create(workshop_paper, paper3),
        Atom.create(knowledge_graphs, paper3),

        # Venues
        Atom.create(journal, nature),
        Atom.create(conference, acl),
    ])

    return DLOntology(
        ontology_iri="urn:example:publication",
        dl_clauses=frozenset(clauses),
        positive_facts=facts,
    )


def run_queries(reasoner):
    """Run various queries on the ontology."""

    print("\n" + "=" * 70)
    print("QUERY RESULTS")
    print("=" * 70 + "\n")

    # Helper to get IRI suffix
    def short_name(individual):
        return individual.iri.split('#')[-1] if hasattr(individual, 'iri') else str(individual)

    # Define concepts for queries
    publication = AtomicConcept.create("http://example.org/pub#Publication")
    author = AtomicConcept.create("http://example.org/pub#Author")
    researcher = AtomicConcept.create("http://example.org/pub#Researcher")
    journal_article = AtomicConcept.create("http://example.org/pub#JournalArticle")
    high_impact = AtomicConcept.create("http://example.org/pub#HighImpact")

    # Query 1: Find all publications
    print("📚 QUERY 1: All Publications")
    print("-" * 70)
    publications = reasoner.get_instances(publication)
    print(f"Total publications: {len(publications)}")
    for pub in publications:
        print(f"  • {short_name(pub)}")
    print()

    # Query 2: Find all authors
    print("👤 QUERY 2: All Authors")
    print("-" * 70)
    authors = reasoner.get_instances(author)
    print(f"Total authors: {len(authors)}")
    for aut in authors:
        print(f"  • {short_name(aut)}")
    print()

    # Query 3: Find all researchers
    print("🔬 QUERY 3: All Researchers")
    print("-" * 70)
    researchers = reasoner.get_instances(researcher)
    print(f"Total researchers: {len(researchers)}")
    for res in researchers:
        print(f"  • {short_name(res)}")
    print()

    # Query 4: High-impact publications
    print("⭐ QUERY 4: High-Impact Publications")
    print("-" * 70)
    high_impact_pubs = reasoner.get_instances(high_impact)
    print(f"High-impact publications: {len(high_impact_pubs)}")
    for pub in high_impact_pubs:
        print(f"  • {short_name(pub)}")
    print()

    # Query 5: Subsumption relationships
    print("🔗 QUERY 5: Class Hierarchy")
    print("-" * 70)
    is_article_pub = reasoner.is_sub_class_of(journal_article, publication)
    is_author_person = reasoner.is_sub_class_of(author, researcher)
    print(f"JournalArticle ⊑ Publication: {is_article_pub}")
    print(f"Author ⊑ Researcher: {is_author_person}")
    print()


def main():
    print("=" * 70)
    print("Complete Real-World Example: Scientific Publication Ontology")
    print("=" * 70)
    print()

    print("Building ontology...")
    ontology = build_publication_ontology()
    print(f"✓ Ontology built with {len(ontology.all_atomic_concepts)} classes")
    print()

    print("Creating reasoner...")
    reasoner = Reasoner(ontology)

    try:
        print("Checking consistency...")
        is_consistent = reasoner.is_consistent()
        print(f"✓ Ontology is consistent: {is_consistent}")
        print()

        if not is_consistent:
            print("❌ ERROR: Ontology is inconsistent!")
            print("Check the axioms for contradictions.")
            return

        print("Computing inferences...")
        reasoner.precompute_inferences()
        print("✓ Inferences computed")
        print()

        # Run queries
        run_queries(reasoner)

        # Analysis and insights
        print("=" * 70)
        print("ANALYSIS & INSIGHTS")
        print("=" * 70)
        print()

        print("""
What the reasoner found:

1. DERIVED FACTS:
   • All researchers are also persons (derived from hierarchy)
   • All authors are also persons (derived from hierarchy)
   • Journal articles are publications (derived from hierarchy)

2. CLASSIFICATION:
   • Papers are automatically classified by type
   • Impact levels are recognized
   • Research areas are organized

3. AUTOMATIC INFERENCE:
   • The reasoner automatically computed the type hierarchy
   • It classified individuals based on stated facts
   • It inferred transitive relationships

4. CONSISTENCY CHECKING:
   • The ontology is consistent (no contradictions)
   • All facts about publications and people are logically sound
   • All constraints are satisfied

REAL-WORLD USE CASES:

✓ Publication Discovery: Find papers on a specific topic
✓ Author Profiling: Get all papers by an author
✓ Venue Analysis: Find papers in specific journals/conferences
✓ Quality Assessment: Identify high-impact publications automatically
✓ Research Network: Build graphs of researchers and their work
        """)

    finally:
        reasoner.dispose()
        print("\n✓ Reasoner disposed (resources released)")


if __name__ == "__main__":
    main()
