from finsight_agent.embeddings import HashEmbeddingProvider
from finsight_agent.store import SQLiteResearchStore
def test_embeddings_are_persisted_and_searchable(tmp_path):
 store=SQLiteResearchStore(str(tmp_path/'research.sqlite3'));text='Revenue grew to Rs. 500 crore. EBITDA was Rs. 80 crore.';embeddings=HashEmbeddingProvider();store.index('doc','sample.pdf',[{'id':'chunk-1','page':1,'text':text}],embeddings.embed([text]));hits=store.search('doc',embeddings.embed(['revenue growth'])[0]);assert hits[0]['page']==1;assert 'Revenue' in hits[0]['text']
