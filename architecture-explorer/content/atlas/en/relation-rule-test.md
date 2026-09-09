Reject unknown predicates while preserving valid typed relations. Candidates with numeric or string values must not bypass validation.

<!-- DEPTH -->

### Why this responsibility exists

Keep semantic names and relationship constraints explicit and versioned.

### Inputs and outputs

Input: EntityRef and AssertionChange candidates.

Output: Validated typed relations or a validation error.

### What must be preserved

- config/ontology.yaml version and vocabulary.
- Unknown types and object relations must be rejected. F5 tracks the scalar-value path bypassing predicate validation.

### Follow the example

Two names appearing together do not justify an arbitrary relationship. Check registered predicates and endpoint types, while distinguishing rule validation from factual truth.

### Avoid this misconception

Unknown types and object relations must be rejected. F5 tracks the scalar-value path bypassing predicate validation.
