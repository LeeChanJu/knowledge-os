Parsing obtains text structure from the file or connector output. Handling a format does not interpret or approve the meaning of a statement.

<!-- DEPTH -->

### Why this responsibility exists

Retain useful evidence text and source provenance while normalizing supported document formats.

### Inputs and outputs

Input: Supported file bytes or provider blocks and properties.

Output: Text, title, URI, and parser version.

### What must be preserved

- No independent store; text is passed to ingestion.
- Processing versions contribute to evidence identity. Transcript timestamps remain part of the evidence text.

### Follow the example

Extracting readable text from an exported note does not establish a relation between two technologies. Format parsing and knowledge judgment are different tasks.

### Avoid this misconception

Processing versions contribute to evidence identity. Transcript timestamps remain part of the evidence text.
