from unittest.mock import patch
from vector_store import prepare_document_records

path = "docs_raw/linux_gateway_day60_full_system_integration.md"

with patch("vector_store.embed_texts") as mock_embed:
    mock_embed.side_effect = lambda texts: [
        [0.0] * 1024 for _ in texts
    ]
    ids,documents,metadatas,embeddings=prepare_document_records(path)
    print(f"{len(ids)}  {len(documents)}  {len(metadatas)}  {len(embeddings)}")
    assert len(ids)==22
    assert len(documents)==22
    assert len(metadatas)==22
    assert len(embeddings)==22
    mock_embed.assert_called_once()
    print("Mock Embedding call count:", mock_embed.call_count)
