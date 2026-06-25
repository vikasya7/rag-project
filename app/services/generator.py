"""
Builds the final prompt from reranked chunks and streams the LLM answer
token by token via an async generator, for use with FastAPI's
StreamingResponse — no WebSocket needed.
"""


