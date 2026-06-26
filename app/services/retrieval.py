"""
Hybrid retrieval: combines dense vector search (semantic) with Postgres
full-text search (lexical), merged with Reciprocal Rank Fusion (RRF).
"""

from app.db.queries import vector_search, keyword_search
from app.services.embedder import embed_query

RRF_K = 60

def _reciprocal_rank_fusion(lists:list[list[dict]])->list[dict]:
    scores:dict[int,dict]={}
    for result_list in lists:
        for rank,row in enumerate(result_list):
            contribution=1/(RRF_K+rank+1)
            if row["id"] in scores:
                scores[row["id"]]["score"]+=contribution
            else:
                scores[row["id"]]={"row":row,"score":contribution}
    
    fused=sorted(scores.values(),key=lambda x:x["score"],reverse=True)
    return [
        {**item["row"] ,"score":item["score"]} for item in fused
    ]


async def hybrid_retrieve(repo_id:int,query:str,candidate_pool_size:int=20)->list[dict]:
    query_embedding=await embed_query(query)
    vector_results=await vector_search(repo_id,query_embedding,candidate_pool_size)
    keyword_results=await keyword_search(repo_id,query,candidate_pool_size)

    fused=_reciprocal_rank_fusion([vector_results,keyword_results])
    return fused[:candidate_pool_size]