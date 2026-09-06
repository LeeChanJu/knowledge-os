DROP INDEX chunk_embedding_vector IF EXISTS;

CREATE VECTOR INDEX chunk_embedding_vector IF NOT EXISTS
FOR (n:Chunk) ON n.embedding
WITH [n.active, n.embedding_model, n.embedding_version]
OPTIONS {indexConfig: {
  `vector.dimensions`: 1536,
  `vector.similarity_function`: 'cosine'
}};
