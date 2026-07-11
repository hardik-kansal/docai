example output format

data: {"type": "thought", "content": "**Considering Label Smoothing**\n\nI'm currently focused on dissecting the user's interest in \"label smoothing.\" My initial analysis hinges on the explicit mention of employing label smoothing with a value of epsilon. I'm aiming to ascertain the full context and what they specifically require related to it.\n\n\n"}

data: {"type": "structured_json_delta", "content": "{\n  \"answer"}

data: {"type": "structured_json_delta", "content": "\": \"During training, a label smoothing value of \u03f5ls = 0.1 was employed. Although this technique makes the model more unsure"}

data: {"type": "structured_json_delta", "content": "\u2014which negatively impacts perplexity\u2014it results in improvements to both accuracy and the BLEU score.\",\n  \"citations\":"}

data: {"type": "structured_json_delta", "content": " [\n    {\n      \"chunk_id\": \"1\",\n      \"quote\": \"During training, we employed label smoothing of value \u03f5 ls = 0 . 1 [36]. This hurts perplexity, as the model learns to be more"}

data: {"type": "structured_json_delta", "content": " unsure, but improves accuracy and BLEU score.\"\n    }\n  ],\n  \"confidence\": 1."}

data: {"type": "structured_json_delta", "content": "0,\n  \"abstained\": false,\n  \"abstain_reason\": \"none\"\n}"}

data: {"type": "usage", "content": "total_input_tokens=1250 input_tokens_by_modality=[ModalityTokens(modality='text', tokens=1250)] total_cached_tokens=0 cached_tokens_by_modality=None total_output_tokens=160 output_tokens_by_modality=None total_tool_use_tokens=0 tool_use_tokens_by_modality=None total_thought_tokens=465 total_tokens=1875 grounding_tool_count=None"}