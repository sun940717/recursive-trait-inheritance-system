# Terminology — RTIS Core Definitions

## 1. Trait

The fundamental unit of the system.

A trait can represent:
- structure
- behavior
- appearance
- material properties

Traits are:
- attachable
- inheritable
- mutable
- composable

---

## 2. BodyGraph

The structural representation of an organism.

- Nodes = PartNodes
- Edges = relationships (attachment / connection)

BodyGraph replaces traditional skeleton-based models.

---

## 3. PartNode

A node within the BodyGraph.

Each PartNode contains:
- geometry (shape representation)
- semantic tags
- morphology features
- anchors (attachment points)

---

## 4. Genome

A set of generative rules.

Genome does NOT directly describe shape.

Instead, it defines:
- how structures grow
- how traits are applied
- how development occurs

---

## 5. Development Engine

Transforms Genome into BodyGraph.

Responsible for:
- growth
- branching
- structural formation
- semantic assignment

---

## 6. TraitDescriptor

A structured definition of a trait.

Defines:
- semantic requirements
- mapping behavior
- inheritance rules
- fallback strategy

---

## 7. Semantic Tags

Tags that describe the role of a PartNode.

Examples:
- grasping
- sensor
- locomotion
- support
- connector

Used instead of fixed anatomical naming.

---

## 8. TraitSlot

A semantic attachment slot.

Example:
- grasping_end_effector
- sensor_cluster

TraitSlots allow mapping across:
- different shapes
- different part counts

---

## 9. Part Correspondence Engine (PCE)

Resolves mapping between traits and target parts.

Instead of:
- matching names (hand → hand)

It uses:
- semantic similarity
- morphology similarity
- topology

---

## 10. Mapping Policy

Defines how traits are applied to target parts.

Examples:
- one-to-many
- top-k selection
- distribution transfer

---

## 11. Fallback

Behavior when no suitable target exists.

Types:
- create new part
- translate trait
- skip

---

## 12. Mutation

Changes applied to Genome or Traits.

Types:
- parameter mutation
- gene duplication
- gene deletion
- regulatory mutation

---

## 13. Evolution

The process of generating new individuals.

Includes:
- reproduction
- mutation
- development
- trait mapping

---

## 14. Unbounded Morphology

A system property where:

- no fixed structure exists
- no limit on part count
- no predefined anatomy

---

## 15. Recursive Attachment

Traits can attach to any other trait.

Examples:
- hand on head
- head on hand
- eye on eye

This enables infinite structural variation.
