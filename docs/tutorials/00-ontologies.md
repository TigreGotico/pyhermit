# Tutorial 0: What is an Ontology?

Your foundational guide to ontologies and why they matter.

## What is an Ontology?

An **ontology** is a formal, machine-readable specification of concepts and their relationships in a domain. Think of it as a structured dictionary + grammar combined.

### Simple Analogy

A traditional database:
```
Employee(name: string, salary: number)
```

An ontology:
```
Employee is a Person
Employee has a salary
Manager is an Employee
Manager supervises at least 1 Employee
```

The ontology **describes relationships and rules**, not just fields.

## Why Ontologies?

### Problem: Data Silos

Company A's database:
```
employee, worker, staff_member  # Same concept, different names
```

Company B's database:
```
personnel, agent, person  # Same concept, different names
```

**How do you integrate data?** Manually? Expensive. Error-prone.

### Solution: Ontologies

Define a shared vocabulary:
```
Employee is an official concept
Employee ⊆ Person
Employee has properties: name, salary, department
```

Now both companies can map their data to the ontology. **Integration is automatic**.

## Real-World Examples

### Healthcare
```
Disease ⊆ MedicalCondition
Symptom of Disease:
  - Flu has symptoms: fever, cough
  - Pneumonia has symptoms: fever, cough, chest_pain
  - Diagnosis: if fever ∧ cough then (Flu ∨ Pneumonia)
```

### E-Commerce
```
Product ⊆ Item
Book is a Product
Author wrote Book
Customer purchases Product
Recommendation: if (Customer purchased Book1) ∧ 
               (Book1.author wrote Book2) then recommend Book2
```

### Scientific Research
```
Protein is a BiologicalEntity
Gene codes for Protein
Mutation affects Gene
Disease associated with Protein
Query: Which diseases are affected by mutations in this gene?
```

## Key Concepts

### 1. Classes (Concepts)
**What:** Categories or types
```
Person, Employee, Manager, Student
```

### 2. Properties (Relationships)
**What:** Connections between things
```
manages (Manager manages Employee)
worksFor (Employee works for Department)
hasSkill (Person has Skill)
```

### 3. Axioms (Rules)
**What:** Logical constraints
```
Employee ⊆ Person  (Every Employee is a Person)
Manager ⊆ Employee (Every Manager is an Employee)
worksFor(x, y) ∧ worksFor(y, z) → worksFor(x, z)  (Transitivity)
```

### 4. Individuals (Data)
**What:** Actual instances
```
alice: Person
bob: Manager
alice manages bob
```

## Ontology vs Database

| Aspect | Database | Ontology |
|--------|----------|----------|
| **Purpose** | Store data | Represent knowledge |
| **Schema** | Fixed tables | Flexible classes |
| **Relationships** | Foreign keys | Rich properties |
| **Reasoning** | SQL queries | Logical inference |
| **Integration** | Difficult | Natural (shared vocabulary) |
| **Expressiveness** | Low | High |

## How Reasoning Works

Given an ontology:
```
Dog ⊆ Animal
Fido: Dog
```

The reasoner automatically infers:
```
Fido: Animal  (not explicitly stated, but logically follows)
```

This is **semantic reasoning** — understanding *meaning*, not just matching strings.

## Types of Ontologies

### 1. Lightweight Ontologies
**Characteristics:** Simple hierarchies, few constraints
```
Animal
  ├─ Mammal
  ├─ Bird
  └─ Fish
```
**Use Case:** Simple taxonomies, catalogs

### 2. Heavyweight Ontologies
**Characteristics:** Rich constraints, complex rules
```
Person ⊆ Agent ⊓ ∃hasAge.Integer ⊓ ∀hasAge.{0..150}
Manager ⊆ Employee ⊓ ∃supervises.Employee ⊓ ≤10supervises
```
**Use Case:** Knowledge bases, decision support systems

### 3. Upper Ontologies
**Characteristics:** Very general concepts (Thing, Event, Location)
```
Thing
  ├─ PhysicalObject
  ├─ AbstractObject
  └─ Event
```
**Use Case:** Foundation for domain-specific ontologies

## When to Use Ontologies

### ✅ Good Use Cases
- **Data Integration:** Unifying multiple data sources
- **Knowledge Representation:** Capturing expert knowledge
- **Semantic Search:** Finding related concepts, not just keywords
- **Decision Support:** Automated reasoning about complex rules
- **Linked Data:** Publishing data for web-scale integration

### ❌ Not Ideal For
- **Simple Key-Value Lookups:** Use a database
- **Unstructured Text:** Use NLP instead
- **Real-time Analytics on Billions:** Too slow
- **Streaming Data:** Reasoning latency too high

## The Semantic Web Vision

The idea: **Make data on the web machine-readable and interlinked**.

```
Current Web (strings):
  "Alice manages Bob"  (humans can read it)

Semantic Web (ontologies):
  alice: Person
  bob: Person
  manages(alice, bob): true
  Manager ⊆ supervises(_, Person)
  → Infer: alice: Manager (possibly)
```

## From Data to Knowledge

```
Data: raw facts
       "birth_date: 1980-01-15"

Information: data + context
       "Person birth_date: 1980-01-15"

Knowledge: information + rules
       "Alice born 1980-01-15 → Alice age ≥ 40 → Alice eligible for senior discounts"
```

Ontologies turn **data into knowledge** through reasoning.

## Your First Steps

1. **Identify your domain** — What are you modeling? (People, Products, Diseases?)
2. **List key concepts** — What classes matter?
3. **Define relationships** — How do they connect?
4. **Add constraints** — What rules apply?
5. **Test with reasoning** — Does the reasoner infer what you expect?

## Try This

Think about a domain you know well (sports, music, cooking):
- What are the main classes?
- What properties connect them?
- What rules would you express?

Example for sports:
```
Sport: {Football, Basketball, Tennis, ...}
Player has Sport (preferred sport)
Team has Player (roster)
Coach manages Team
Team plays Game
Game has Winner
```

## Next Steps

- **[Installation](../installation.md)** — Set up PyHermit
- **[Concepts](../concepts.md)** — Deeper dive into OWL and DL
- **[First Program](../first-program.md)** — Write your first reasoner code

---

**Key Takeaway:** Ontologies are **formal knowledge representations** that enable machines to reason about relationships, infer new facts, and integrate diverse data sources automatically.
