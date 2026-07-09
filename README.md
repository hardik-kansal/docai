BAAI/bge-small-en-v1.5
[2026-07-07 19:29:05,637: WARNING/ForkPoolWorker-1] document registering time
[2026-07-07 19:29:05,637: WARNING/ForkPoolWorker-1] 4.209919992717914
[2026-07-07 19:29:05,697: WARNING/ForkPoolWorker-1] chunk upsert time
[2026-07-07 19:29:05,697: WARNING/ForkPoolWorker-1] 56.91463701077737
[2026-07-07 19:29:06,325: WARNING/ForkPoolWorker-1] embedding time
[2026-07-07 19:29:06,326: WARNING/ForkPoolWorker-1] 628.9076510001905
[2026-07-07 19:29:06,450: INFO/ForkPoolWorker-1] HTTP Request: PUT http://localhost:6333/collections/contracts/points?wait=true "HTTP/1.1 200 OK"
[2026-07-07 19:29:06,451: WARNING/ForkPoolWorker-1] embeding index time
[2026-07-07 19:29:06,451: WARNING/ForkPoolWorker-1] 125.66903399419971
[2026-07-07 19:29:06,463: INFO/ForkPoolWorker-1] Task ingestion.tasks.process_document_task[3d92a0a5-8029-45c6-8e0a-ebba2473f8ba] succeeded in 5.278648528008489s: None'




status='completed' 
model='gemini-3.5-flash' 
agent=None id='v1_ChdhVUpPYXM3X01iR0FnOFVQcUlxRGdBdxIXYVVKT2FzN19NYkdBZzhVUHFJcURnQXc' created='2026-07-08T12:28:25Z' 
updated='2026-07-08T12:28:25Z' 
system_instruction=None 
tools=None 
usage=Usage(
    total_input_tokens=1250, 
    input_tokens_by_modality=[ModalityTokens(modality='text', tokens=1250)], total_cached_tokens=0, 
    cached_tokens_by_modality=None, 
    total_output_tokens=150, 
    output_tokens_by_modality=None, 
    total_tool_use_tokens=0, 
    tool_use_tokens_by_modality=None, 
    total_thought_tokens=217, 
    total_tokens=1617, 
    grounding_tool_count=None) 
response_modalities=None 
response_mime_type=None 
previous_interaction_id=None 
environment_id=None 
service_tier='standard' 
webhook_config=None 
steps=[
    ThoughtStep(type='thought', signature='...', summary=None),
    ModelOutputStep(
        type='model_output', 
        content=[
            TextContent(
                text='{
                    \n  "answer": "During training, label smoothing of value \\u0335_ls = 0.1 was employed. Although this hurts perplexity because the model learns to be more unsure, it improves both accuracy and the BLEU score.",\n  
                    "citations": [\n    
                        {\n      
                        "chunk_id": "1",\n      
                        "quote": "Label Smoothing During training, we employed label smoothing of value ϵ ls = 0 . 1 [36]. This hurts perplexity, as the model learns to be more unsure, but improves accuracy and BLEU score."\n
                        }\n  
                            ],\n  
                    "confidence": 1.0,\n  
                    "abstained": false\n
                        }',
                type='text', 
                annotations=None
                )
                ],
        error=None)
    ] 
response_format=None 
environment=None 
generation_config=None 
cached_content=None 
agent_config=None 
input=None 
output_text='{\n  
    "answer": "During training, label smoothing of value \\u0335_ls = 0.1 was employed. Although this hurts perplexity because the model learns to be more unsure, it improves both accuracy and the BLEU score.",\n  
    "citations": [\n    
                    {\n      
                        "chunk_id": "1",\n      
                        "quote": "Label Smoothing During training, we employed label smoothing of value ϵ ls = 0 . 1 [36]. This hurts perplexity, as the model learns to be more unsure, but improves accuracy and BLEU score."\n   
                    }\n 
                ],\n 
  "confidence": 1.0,\n 
   "abstained": false\n
   }' 
output_image=None 
output_audio=None 
output_video=None 
object='interaction'








