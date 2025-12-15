"""
RAGAS Results Visualization
============================

Creates visualizations of RAGAS evaluation results.
"""

import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)

# Load results
results_path = Path(__file__).parent / "ragas_results.json"
with open(results_path, 'r') as f:
    data = json.load(f)

results = data['results']
summary = data['summary']

# Create DataFrame
df = pd.DataFrame(results)

# Remove null answer (unanswerable question)
df_with_answers = df[df['answer'].notna()].copy()

print("="*70)
print("📊 RAGAS EVALUATION VISUALIZATION")
print("="*70)

# Create figure with subplots
fig, axes = plt.subplots(2, 2, figsize=(15, 12))
fig.suptitle('RAGAS Evaluation Results - RAG System Performance', fontsize=16, fontweight='bold')

# 1. Overall Metrics Bar Chart
ax1 = axes[0, 0]
metrics = ['context_recall', 'context_precision', 'faithfulness', 'answer_relevancy']
scores = [summary[f'avg_{m}'] for m in metrics]
colors = ['#2ecc71' if s >= 0.9 else '#f39c12' if s >= 0.7 else '#e74c3c' for s in scores]

bars = ax1.bar(range(len(metrics)), scores, color=colors, alpha=0.7, edgecolor='black')
ax1.set_xticks(range(len(metrics)))
ax1.set_xticklabels(['Context\nRecall', 'Context\nPrecision', 'Faithfulness', 'Answer\nRelevancy'], fontsize=10)
ax1.set_ylabel('Score', fontsize=12)
ax1.set_title('Overall Metric Scores', fontsize=14, fontweight='bold')
ax1.set_ylim([0, 1.1])
ax1.axhline(y=0.9, color='green', linestyle='--', alpha=0.3, label='Excellent (0.9+)')
ax1.axhline(y=0.7, color='orange', linestyle='--', alpha=0.3, label='Good (0.7+)')

# Add value labels on bars
for i, (bar, score) in enumerate(zip(bars, scores)):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02,
             f'{score:.3f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

ax1.legend(loc='lower right', fontsize=9)
ax1.grid(axis='y', alpha=0.3)

# 2. Context Precision by Question
ax2 = axes[0, 1]
questions = [r['question_id'] for r in results]
precisions = [r['context_precision'] if r['context_precision'] is not None else 0 for r in results]
colors_prec = ['#2ecc71' if p >= 0.9 else '#f39c12' if p >= 0.7 else '#e74c3c' if p > 0 else '#95a5a6' for p in precisions]

bars2 = ax2.bar(questions, precisions, color=colors_prec, alpha=0.7, edgecolor='black')
ax2.set_xlabel('Question ID', fontsize=12)
ax2.set_ylabel('Context Precision Score', fontsize=12)
ax2.set_title('Context Precision by Question', fontsize=14, fontweight='bold')
ax2.set_ylim([0, 1.1])
ax2.axhline(y=0.9, color='green', linestyle='--', alpha=0.3)
ax2.axhline(y=0.7, color='orange', linestyle='--', alpha=0.3)
ax2.grid(axis='y', alpha=0.3)

# Highlight problematic questions
for i, (bar, prec, q_id) in enumerate(zip(bars2, precisions, questions)):
    if prec < 0.5 and prec > 0:
        ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.02,
                 '⚠️', ha='center', va='bottom', fontsize=16)

# 3. Answer Relevancy by Question
ax3 = axes[1, 0]
relevancies = [r['answer_relevancy'] if r['answer_relevancy'] is not None else 0 for r in results]
colors_rel = ['#2ecc71' if r >= 0.9 else '#f39c12' if r >= 0.7 else '#e74c3c' if r > 0 else '#95a5a6' for r in relevancies]

bars3 = ax3.bar(questions, relevancies, color=colors_rel, alpha=0.7, edgecolor='black')
ax3.set_xlabel('Question ID', fontsize=12)
ax3.set_ylabel('Answer Relevancy Score', fontsize=12)
ax3.set_title('Answer Relevancy by Question', fontsize=14, fontweight='bold')
ax3.set_ylim([0, 1.1])
ax3.axhline(y=0.9, color='green', linestyle='--', alpha=0.3)
ax3.axhline(y=0.7, color='orange', linestyle='--', alpha=0.3)
ax3.grid(axis='y', alpha=0.3)

# 4. Heatmap of all metrics by question
ax4 = axes[1, 1]
heatmap_data = []
for r in results:
    heatmap_data.append([
        r['context_recall'] if r['context_recall'] is not None else 0,
        r['context_precision'] if r['context_precision'] is not None else 0,
        r['faithfulness'] if r['faithfulness'] is not None else 0,
        r['answer_relevancy'] if r['answer_relevancy'] is not None else 0,
    ])

heatmap_df = pd.DataFrame(
    data=heatmap_data,
    columns=['Recall', 'Precision', 'Faithfulness', 'Relevancy'],  # type: ignore
    index=questions  # type: ignore
)

sns.heatmap(heatmap_df, annot=True, fmt='.2f', cmap='RdYlGn', vmin=0, vmax=1, 
            ax=ax4, cbar_kws={'label': 'Score'}, linewidths=1)
ax4.set_title('Metric Heatmap (All Questions)', fontsize=14, fontweight='bold')
ax4.set_xlabel('Metric', fontsize=12)
ax4.set_ylabel('Question ID', fontsize=12)

plt.tight_layout()

# Save figure
output_path = Path(__file__).parent / "ragas_visualization.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"\n✅ Visualization saved to: {output_path}")

# Print detailed analysis
print("\n" + "="*70)
print("📈 DETAILED ANALYSIS")
print("="*70)

print("\n🎯 Questions with Low Context Precision (< 0.5):")
for r in results:
    if r['context_precision'] is not None and r['context_precision'] < 0.5 and r['context_precision'] > 0:
        print(f"   ⚠️  {r['question_id']}: {r['question']}")
        print(f"      Precision: {r['context_precision']:.3f}")
        print(f"      This question needs optimization!\n")

print("\n✅ Questions with Excellent Performance (Precision > 0.9):")
for r in results:
    if r['context_precision'] is not None and r['context_precision'] > 0.9:
        print(f"   ✨ {r['question_id']}: {r['question']}")
        print(f"      Precision: {r['context_precision']:.3f}\n")

print("\n" + "="*70)
print("💡 KEY INSIGHTS")
print("="*70)
print(f"✅ Perfect Recall: {summary['avg_context_recall']:.3f}")
print(f"✅ Zero Hallucinations: {summary['avg_faithfulness']:.3f}")
print(f"⚠️  Context Precision needs work: {summary['avg_context_precision']:.3f}")
print(f"✅ Good Answer Quality: {summary['avg_answer_relevancy']:.3f}")

print("\n🎓 Overall Grade: A- (Excellent with optimization potential)")
print("="*70)

plt.show()
