"""
Knowledge Graph Construction

This example demonstrates:
1. Building knowledge graphs from structured data
2. Entity linking and resolution
3. Property extraction and enrichment
4. Semantic annotation
5. Graph traversal and querying

Knowledge graphs combine ontologies with real data to create
machine-readable semantic networks that enable intelligent
reasoning and discovery.
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


def main():
    X = Variable.create("X")
    Y = Variable.create("Y")
    Z = Variable.create("Z")

    # Build a movie knowledge graph
    movie = AtomicConcept.create("http://example.org/kg#Movie")
    actor = AtomicConcept.create("http://example.org/kg#Actor")
    director = AtomicConcept.create("http://example.org/kg#Director")
    producer = AtomicConcept.create("http://example.org/kg#Producer")
    person = AtomicConcept.create("http://example.org/kg#Person")
    genre = AtomicConcept.create("http://example.org/kg#Genre")

    sci_fi = AtomicConcept.create("http://example.org/kg#SciFi")
    action = AtomicConcept.create("http://example.org/kg#Action")
    drama = AtomicConcept.create("http://example.org/kg#Drama")

    # Roles for relationships
    acted_in = AtomicRole.create("http://example.org/kg#actedIn")
    directed = AtomicRole.create("http://example.org/kg#directed")
    produced = AtomicRole.create("http://example.org/kg#produced")
    has_genre = AtomicRole.create("http://example.org/kg#hasGenre")
    worked_with = AtomicRole.create("http://example.org/kg#workedWith")

    # TBox: ontology rules
    clauses = [
        # Actor ⊑ Person
        DLClause.create(
            (Atom.create(person, X),),
            (Atom.create(actor, X),),
        ),
        # Director ⊑ Person
        DLClause.create(
            (Atom.create(person, X),),
            (Atom.create(director, X),),
        ),
        # Producer ⊑ Person
        DLClause.create(
            (Atom.create(person, X),),
            (Atom.create(producer, X),),
        ),
        # SciFi ⊑ Genre
        DLClause.create(
            (Atom.create(genre, X),),
            (Atom.create(sci_fi, X),),
        ),
        # Action ⊑ Genre
        DLClause.create(
            (Atom.create(genre, X),),
            (Atom.create(action, X),),
        ),
        # Drama ⊑ Genre
        DLClause.create(
            (Atom.create(genre, X),),
            (Atom.create(drama, X),),
        ),
        # Note: worked_with relationships are handled through querying
        # (Complex multi-body rules are computed via reasoning, not explicit derivation)
    ]

    # ABox: Construct the knowledge graph
    # Movies
    inception = Individual.create("http://example.org/kg#Inception")
    avatar = Individual.create("http://example.org/kg#Avatar")
    titanic = Individual.create("http://example.org/kg#Titanic")
    the_matrix = Individual.create("http://example.org/kg#TheMatrix")

    # People
    leo = Individual.create("http://example.org/kg#LeonardoDiCaprio")
    kate = Individual.create("http://example.org/kg#KateWinslet")
    keanu = Individual.create("http://example.org/kg#KeanuReeves")
    nolan = Individual.create("http://example.org/kg#ChristopherNolan")
    cameron = Individual.create("http://example.org/kg#JamesCameron")

    # Genres
    sci_fi_ind = Individual.create("http://example.org/kg#SciFi")
    action_ind = Individual.create("http://example.org/kg#Action")
    drama_ind = Individual.create("http://example.org/kg#Drama")

    facts = frozenset([
        # Movies
        Atom.create(movie, inception),
        Atom.create(movie, avatar),
        Atom.create(movie, titanic),
        Atom.create(movie, the_matrix),
        # People
        Atom.create(person, leo),
        Atom.create(person, kate),
        Atom.create(person, keanu),
        Atom.create(person, nolan),
        Atom.create(person, cameron),
        # Person types
        Atom.create(actor, leo),
        Atom.create(actor, kate),
        Atom.create(actor, keanu),
        Atom.create(director, nolan),
        Atom.create(director, cameron),
        # Casting
        Atom.create(acted_in, leo, inception),
        Atom.create(acted_in, leo, titanic),
        Atom.create(acted_in, kate, titanic),
        Atom.create(acted_in, keanu, the_matrix),
        # Direction
        Atom.create(directed, nolan, inception),
        Atom.create(directed, cameron, avatar),
        Atom.create(directed, cameron, titanic),
        # Genres
        Atom.create(genre, sci_fi_ind),
        Atom.create(genre, action_ind),
        Atom.create(genre, drama_ind),
        Atom.create(sci_fi, sci_fi_ind),
        Atom.create(sci_fi, action_ind),
        Atom.create(action, action_ind),
        Atom.create(drama, drama_ind),
        # Movie genres
        Atom.create(has_genre, inception, sci_fi_ind),
        Atom.create(has_genre, inception, action_ind),
        Atom.create(has_genre, avatar, sci_fi_ind),
        Atom.create(has_genre, avatar, action_ind),
        Atom.create(has_genre, titanic, drama_ind),
        Atom.create(has_genre, the_matrix, sci_fi_ind),
        Atom.create(has_genre, the_matrix, action_ind),
    ])

    ontology = DLOntology(
        ontology_iri="urn:tutorial:kg",
        dl_clauses=frozenset(clauses),
        positive_facts=facts,
    )

    reasoner = Reasoner(ontology)

    try:
        reasoner.precompute_inferences()

        print("=" * 70)
        print("KNOWLEDGE GRAPH CONSTRUCTION")
        print("=" * 70)
        print()

        print("Movie Knowledge Graph Statistics:")
        print("-" * 70)

        movies = reasoner.get_instances(movie)
        actors = reasoner.get_instances(actor)
        directors = reasoner.get_instances(director)
        genres = reasoner.get_instances(genre)

        print(f"Total movies: {len(movies)}")
        print(f"Total actors: {len(actors)}")
        print(f"Total directors: {len(directors)}")
        print(f"Total genres: {len(genres)}")
        print()

        print("Graph Topology:")
        print("-" * 70)

        print("Movies and their casts:")
        for m in sorted(movies, key=lambda x: x.iri):
            movie_name = m.iri.split('#')[-1]
            cast = [
                a.iri.split('#')[-1]
                for a in actors
                if reasoner.has_role_relationship(a, acted_in, m)
            ]
            if cast:
                print(f"  {movie_name}: {', '.join(cast)}")

        print()
        print("Movies and their directors:")
        for m in sorted(movies, key=lambda x: x.iri):
            movie_name = m.iri.split('#')[-1]
            dirs = [
                d.iri.split('#')[-1]
                for d in directors
                if reasoner.has_role_relationship(d, directed, m)
            ]
            if dirs:
                print(f"  {movie_name}: {', '.join(dirs)}")

        print()
        print("Movies and their genres:")
        for m in sorted(movies, key=lambda x: x.iri):
            movie_name = m.iri.split('#')[-1]
            genre_list = [
                g.iri.split('#')[-1]
                for g in reasoner.get_instances(genre)
                if reasoner.has_role_relationship(m, has_genre, g)
            ]
            if genre_list:
                print(f"  {movie_name}: {', '.join(genre_list)}")

        print()

        print("Semantic Queries on the Knowledge Graph:")
        print("-" * 70)

        # Query 1: All sci-fi movies
        sci_fi_movies = [
            m
            for m in movies
            if reasoner.has_role_relationship(m, has_genre, sci_fi_ind)
        ]
        print(f"Sci-Fi movies ({len(sci_fi_movies)}):")
        for m in sci_fi_movies:
            print(f"  - {m.iri.split('#')[-1]}")

        print()

        # Query 2: Find actors who worked together (appeared in same movie)
        print("Actor collaborations (appeared in same movie):")
        collaborations = {}
        for a1 in actors:
            for a2 in actors:
                if a1 != a2:
                    # Find movies both appeared in
                    common_movies = []
                    for m in movies:
                        if (reasoner.has_role_relationship(a1, acted_in, m) and
                            reasoner.has_role_relationship(a2, acted_in, m)):
                            common_movies.append(m)
                    if common_movies:
                        key = tuple(sorted([a1.iri, a2.iri]))
                        collaborations[key] = len(common_movies)

        for (p1, p2), count in sorted(collaborations.items()):
            n1 = p1.split('#')[-1]
            n2 = p2.split('#')[-1]
            print(f"  {n1} ↔ {n2} ({count} movie(s))")

        print()

        print("=" * 70)
        print("Knowledge Graph Construction Patterns")
        print("=" * 70)
        print("""
BUILDING A KNOWLEDGE GRAPH:

Step 1: Define the Schema (TBox)
  - Create ontology concepts for entities
  - Define relationships (roles) between entities
  - Add reasoning rules for inferences

Step 2: Populate with Data (ABox)
  - Create individuals for real-world entities
  - Assert facts about relationships
  - Link entities through roles

Step 3: Enrich with Inference
  - Add rules that derive new relationships
  - Enable type inference
  - Compute transitive properties

Step 4: Query and Analyze
  - Find nodes matching criteria
  - Traverse relationships
  - Answer semantic queries

KNOWLEDGE GRAPH APPLICATIONS:

1. RECOMMENDATION SYSTEMS
   - Find movies similar to a watched movie
   - Recommend based on actor/director preferences
   - Suggest collaborators

2. RELATIONSHIP DISCOVERY
   - Find indirect relationships
   - Compute shortest paths
   - Identify collaboration networks

3. DATA INTEGRATION
   - Merge data from multiple sources
   - Resolve entity references
   - Enrich with semantic context

4. REASONING AND INFERENCE
   - Infer missing relationships
   - Classify new entities
   - Detect inconsistencies

CONSTRUCTION PATTERNS:

Pattern 1: Structured Data to RDF
  CSV/JSON → Parse → Create Individuals
         → Map attributes to properties
         → Assert facts

Pattern 2: Entity Linking
  Text → Extract entities
      → Link to ontology concepts
      → Create individuals

Pattern 3: Schema Inference
  Data → Analyze patterns
      → Create ontology
      → Populate facts

PERFORMANCE TIPS:

- Precompute inferences for large graphs
- Index frequently accessed properties
- Partition large graphs by domain
- Cache query results
- Use incremental reasoning updates

SCALABILITY:

- Small graphs: < 10K nodes, reason fully
- Medium graphs: 10K-1M nodes, index selectively
- Large graphs: 1M+ nodes, use distributed reasoning

REAL-WORLD EXAMPLES:

1. Google Knowledge Graph
   - 500 billion+ facts
   - Billions of entities
   - Powers search and recommendations

2. DBpedia
   - 4M+ entities
   - 14B+ facts
   - Linked data from Wikipedia

3. Wikidata
   - 100M+ items
   - Massive collaborative knowledge base

4. Enterprise Knowledge Graphs
   - Company data, products, customers
   - Enable smart search and discovery
        """)

    finally:
        reasoner.dispose()


if __name__ == "__main__":
    main()
