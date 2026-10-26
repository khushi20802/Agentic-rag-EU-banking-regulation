# Evaluation results (v1)

15 questions, model: openai/gpt-oss-120b (Groq), embeddings: voyage-4

| Category | Questions | Routing | Doc recall | Faithfulness | Correctness | Avg tool calls | Avg tokens | Avg seconds |
|---|---|---|---|---|---|---|---|---|
| catalogue | 3 | 100% | 100% | 79% | 100% | 1.0 | 4,202 | 8 |
| content | 4 | 100% | 100% | 61% | 88% | 1.0 | 6,358 | 42 |
| cross_lingual | 3 | 100% | 67% | 97% | 50% | 2.0 | 10,339 | 68 |
| chained | 3 | 33% | 100% | 84% | 83% | 2.0 | 10,436 | 69 |
| not_in_corpus | 2 | 100% | 100% | 70% | 75% | 4.0 | 11,450 | 74 |
| **All** | 15 | 87% | 93% | 78% | 80% | 1.8 | 8,217 | 50 |

**Reflection test:** 3/3 planted false claims flagged.

## Per question

| ID | Routing | Doc recall | Faithfulness | Correct | Tool calls | Tokens |
|---|---|---|---|---|---|---|
| C1 | ✅ | 100% | 88% | 1 | 1 | 4,106 |
| C2 | ✅ | 100% | 60% | 1 | 1 | 3,742 |
| C3 | ✅ | 100% | 90% | 1 | 1 | 4,758 |
| D1 | ✅ | 100% | 100% | 1 | 1 | 6,214 |
| D2 | ✅ | 100% | 40% | 0.5 | 1 | 6,217 |
| D3 | ✅ | 100% | 14% | 1 | 1 | 5,174 |
| D4 | ✅ | 100% | 90% | 1 | 1 | 7,827 |
| X1 | ✅ | 100% | 100% | 0.5 | 2 | 9,240 |
| X2 | ✅ | 100% | 90% | 0.5 | 3 | 15,152 |
| X3 | ✅ | 0% | 100% | 0.5 | 1 | 6,624 |
| H1 | ✅ | 100% | 80% | 1 | 3 | 14,279 |
| H2 | ❌ | 100% | 83% | 1 | 1 | 6,254 |
| H3 | ❌ | 100% | 90% | 0.5 | 2 | 10,774 |
| N1 | ✅ | 100% | 70% | 0.5 | 4 | 11,403 |
| N2 | ✅ | – | – | 1 | 4 | 11,498 |
