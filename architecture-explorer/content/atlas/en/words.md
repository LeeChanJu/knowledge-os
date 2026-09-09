Use word search when you remember an exact name.

<!-- DEPTH -->

### Why this responsibility exists

Make ranking explainable and model isolation explicit.

### Inputs and outputs

Input: Query, mode, access context and optional vector/model/version.

Output: Ranked evidence and trace ID.

### What must be preserved

- No additional index service.
- Fusion cannot discard authorization requirements.

### Follow the example

Remembering the word “Joule” can locate a candidate with keyword search. Receiving a result does not establish that its passage answers the question.

### Avoid this misconception

Fusion cannot discard authorization requirements.
