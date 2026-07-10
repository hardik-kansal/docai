|  Table 2: The Transformer achieves better BLEU scores than previous state-of-the-art models on the English-to-German and English-to-French newstest2014 tests at a fraction of the training cost.

|  | BLEU | BLEU | Training Cost (FLOPs) | Training Cost (FLOPs) |
| - | - | - | - | - |
| Model | EN-DE | EN-FR | EN-DE | EN-FR |
| ByteNet [18] | 23.75 |  |  | 20 |
| Deep-Att + PosUnk [39] |  | 39.2 | 19 | 1 . 0 · 10 |
| GNMT + RL [38] | 24.6 | 39.92 | 2 . 3 · 10 18 | 20 1 . 4 · 10 20 |
| ConvS2S [9] | 25.16 | 40.46 | 9 . 6 · 10 19 | 1 . 5 · 10 20 |
| MoE [32] | 26.03 | 40.56 | 2 . 0 · 10 | 1 . 2 · 10 |
| Deep-Att + PosUnk Ensemble [39] |  | 40.4 |  | 20 8 . 0 · 10 21 |
| GNMT + RL Ensemble [38] | 26.30 | 41.16 | 20 1 . 8 · 10 19 | 1 . 1 · 10 21 |
| ConvS2S Ensemble [9] | 26.36 | 41.29 | 7 . 7 · 10 | 1 . 2 · 10 |

|  | BLEU | BLEU | Training Cost (FLOPs) | Training Cost (FLOPs) |
| - | - | - | - | - |
| Transformer (base model) | 27.3 | 38.1 | 3 . 3 | · 10 18 19 |
| Transformer (big) | 28.4 | 41.8 | 2 . | 3 · 10 |

Residual Dropout We apply dropout [33] to the output of each sub-layer, before it is added to the sub-layer input and normalized. In addition, we apply dropout to the sums of the embeddings and the positional encodings in both the encoder and decoder stacks. For the base model, we use a rate of Pdrop = 0 . 1 .
Label Smoothing During training, we employed label smoothing of value ϵ ls = 0 . 1 [36]. This hurts perplexity, as the model learns to be more unsure, but improves accuracy and BLEU score.