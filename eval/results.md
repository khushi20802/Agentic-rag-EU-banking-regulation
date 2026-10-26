# Evaluation results

15 questions, model: openai/gpt-oss-120b (Groq), embeddings: voyage-4

| Category | Questions | Routing | Doc recall | Faithfulness | Correctness | Avg tool calls | Avg tokens | Avg seconds |
|---|---|---|---|---|---|---|---|---|
| catalogue | 3 | 100% | 78% | 80% | 100% | 1.0 | 4,353 | 13 |
| content | 4 | 100% | 100% | 85% | 75% | 1.5 | 7,111 | 50 |
| cross_lingual | 3 | 100% | 67% | 93% | 67% | 1.7 | 8,626 | 55 |
| chained | 3 | 67% | 100% | 79% | 67% | 2.3 | 11,065 | 63 |
| not_in_corpus | 2 | 100% | 100% | 33% | 100% | 1.0 | 3,612 | 29 |
| **All** | 15 | 93% | 88% | 81% | 80% | 1.5 | 7,187 | 43 |

**Reflection test:** 3/3 planted false claims flagged.

## Per question

| ID | Routing | Doc recall | Faithfulness | Correct | Tool calls | Tokens |
|---|---|---|---|---|---|---|
| C1 | ✅ | 100% | 100% | 1 | 1 | 4,655 |
| C2 | ✅ | 100% | 100% | 1 | 1 | 3,699 |
| C3 | ✅ | 33% | 40% | 1 | 1 | 4,706 |
| D1 | ✅ | 100% | 100% | 1 | 1 | 6,163 |
| D2 | ✅ | 100% | 70% | 1 | 2 | 7,367 |
| D3 | ✅ | 100% | 80% | 0.5 | 1 | 5,350 |
| D4 | ✅ | 100% | 90% | 0.5 | 2 | 9,564 |
| X1 | ✅ | 100% | 100% | 0.5 | 2 | 8,164 |
| X2 | ✅ | 100% | 90% | 1 | 1 | 7,788 |
| X3 | ✅ | 0% | 90% | 0.5 | 2 | 9,927 |
| H1 | ✅ | 100% | 90% | 1 | 3 | 13,743 |
| H2 | ✅ | 100% | 67% | 0.5 | 2 | 7,632 |
| H3 | ❌ | 100% | 80% | 0.5 | 2 | 11,819 |
| N1 | ✅ | 100% | 33% | 1 | 1 | 3,964 |
| N2 | ✅ | – | – | 1 | 1 | 3,259 |
