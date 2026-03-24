# Recursive Trait Inheritance System (RTIS)

## Overview

RTIS (Recursive Trait Inheritance System) is a generative system for constructing and evolving organisms under **unbounded morphology**.

Unlike traditional character systems, RTIS does not rely on fixed anatomy (e.g. head, arms, legs).

Instead, it is built on:

- Trait-driven composition
- Recursive structural attachment
- Semantic-based correspondence
- Genetic-style inheritance and evolution

---

## Core Idea

In RTIS:

- Everything is a **Trait**
- Organisms are **graphs of traits**
- Structure is **not predefined**
- Traits can attach to any other traits

Example:

- A head can grow from a hand  
- A hand can grow from a head  
- Eyes can grow on other eyes  

This enables **infinite structural variation**.

---

## System Architecture


Genome
↓
Development Engine
↓
BodyGraph
↓
Trait System
↓
Part Correspondence Engine (PCE)
↓
Evolution Loop


---

## Key Concepts

### 1. Unbounded Morphology
- No fixed skeleton
- No predefined hierarchy
- No limit on structure complexity

---

### 2. Trait as Fundamental Unit
Traits define:
- structure
- behavior
- appearance
- material

---

### 3. Recursive Attachment
Traits can attach to any other traits.

---

### 4. Semantic Matching (Not Naming)
Instead of:
- hand → hand

RTIS uses:
- semantic tags
- morphology
- topology

---

### 5. Genetic System
Genome defines:
- growth rules
- structure generation
- mutation behavior

---

## Repository Structure


spec/
system-overview.md
terminology.md
genome-system.md
development-engine.md
reproduction-cycle.md
part-correspondence-engine.md

schema/
trait-descriptor.schema.json
genome.schema.json
bodygraph.schema.json

examples/
traits/
hand_grasping_v1.json
eye_sensor_cluster_v1.json
genomes/
sample_genome_v1.json
bodygraphs/
sample_bodygraph_v1.json


---

## Specification Layers

### Spec (System Design)
Defines:
- architecture
- system behavior
- conceptual models

---

### Schema (Data Structure)
Defines:
- TraitDescriptor
- Genome
- BodyGraph

---

### Examples (Concrete Instances)
Demonstrates:
- real trait definitions
- sample genomes
- generated structures

---

## Example Flow


sample_genome_v1.json
↓
Development Engine
↓
sample_bodygraph_v1.json
↓
Trait Mapping (PCE)
↓
Evolution


---

## Current Status

This repository contains:

- Complete system specifications
- Data schemas
- Example instances

No runtime implementation yet.

---

## Future Work

- Minimal executable prototype (Python / Unity)
- Visualization of BodyGraph
- Evolution simulation
- AI-assisted semantic tagging
- Trait generation models

---

## Positioning

RTIS is not just:

- a character generator
- a procedural modeling tool

It is a:

> **Generative Life System**

Applicable to:
- games
- generative art
- simulation
- artificial life research

---

## Author

Created by:Chen-He Hung


---

## License

MIT License
