# Part Correspondence Engine (PCE)

## 0. Definition

The Part Correspondence Engine (PCE) resolves:

> Where and how a trait should attach across different organisms
> under unbounded morphology.

Traditional systems rely on:
- fixed anatomy (hand, head, leg)
- fixed hierarchy

RTIS does NOT.

---

## 1. Problem Statement

In RTIS:

- organisms have no fixed structure
- part counts vary
- topology varies
- naming is unreliable

Example:

Parent A:
- 2 grasping appendages

Parent B:
- 6 grasping appendages

Question:
Where should a "grasping trait" attach?

---

## 2. Core Principle

### 2.1 No Name-Based Matching

DO NOT use:
- hand → hand
- eye → eye

Use:
- semantic roles
- morphology
- topology

---

## 3. Candidate Extraction

Given a TraitDescriptor:

Extract candidate nodes from target BodyGraph.

### 3.1 Required Tags

Nodes must satisfy:
- required semantic tags

Example:
- grasping
- end_effector

---

### 3.2 Preferred Tags

Used for ranking, not filtering.

---

## 4. Similarity Scoring

Each candidate is scored based on:

### 4.1 Semantic Similarity
Match tag probabilities.

### 4.2 Morphological Similarity
Compare:
- elongation
- branching
- surface features

### 4.3 Topological Position
Compare:
- depth in graph
- leaf vs internal node
- centrality

---

## 5. Mapping Policy

Defines how traits map to candidates.

### 5.1 Top-K Mapping
Select best K nodes.

---

### 5.2 One-to-Many
One source → multiple targets.

---

### 5.3 Distribution Transfer

Trait influence is distributed across targets.

Rules:
- more targets → less weight per node
- weight normalized to 1

---

## 6. TraitSlot

TraitSlots replace anatomical naming.

Example:

- grasping_end_effector#1
- grasping_end_effector#2

Slots are assigned dynamically based on:
- candidate ranking
- mapping policy

---

## 7. Weighting System

Each mapping produces:


target_node + weight


Constraints:
- weights sum to 1
- similarity influences weight
- count reduces individual weight

---

## 8. Fallback Mechanism

When no valid candidate exists:

### 8.1 Create Attachment Part
Generate a new compatible node.

---

### 8.2 Trait Translation
Convert trait into compatible form.

Example:
- hand → claw
- hand → tentacle

---

### 8.3 Skip with Record
Trait not applied but recorded.

---

## 9. AI Integration

AI is used ONLY for:

### 9.1 Semantic Tagging
Assign tag probabilities to nodes.

---

### 9.2 Trait Translation
Generate compatible trait variants.

---

### 9.3 Structure Synthesis
Create new parts when needed.

---

## 10. Output

PCE produces:

- CorrespondenceMap
- FallbackPlan (optional)

---

## 11. CorrespondenceMap Structure

Example:


Trait: grasping

Slots:
grasping_end_effector#1:
- node_17 (0.7)
- node_23 (0.3)

grasping_end_effector#2:
- node_23 (1.0)


---

## 12. System Role

PCE is the ONLY system responsible for:

- cross-organism trait alignment
- structure-agnostic inheritance

Without PCE:
RTIS cannot function under unbounded morphology.
