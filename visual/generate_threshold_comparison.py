#!/usr/bin/env python3
"""
Generate comparison visualization: Default vs Threshold-Tuned Detection
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Results data
models = ['LOF\nDefault', 'LOF\nThreshold-Tuned']
precision = [0.608, 0.941]
recall = [1.0, 1.0]
f1_score = [0.756, 0.970]
false_positives = [113, 11]
false_negatives = [0, 0]

# Create figure with subplots
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
fig.suptitle('Threshold Tuning Impact: Default vs Optimized Detection\n(Lower is Better for FP/FN, Higher for Precision/Recall/F1)', 
             fontsize=16, fontweight='bold', y=1.00)

# Color scheme
color_default = '#FF6B6B'  # Red for default
color_tuned = '#51CF66'    # Green for tuned

# 1. Precision Comparison
ax = axes[0, 0]
bars = ax.bar(models, precision, color=[color_default, color_tuned], alpha=0.8, edgecolor='black', linewidth=1.5)
ax.set_ylabel('Precision', fontsize=12, fontweight='bold')
ax.set_ylim(0, 1.0)
ax.set_title('Precision (Higher is Better)', fontsize=12, fontweight='bold')
for i, (bar, val) in enumerate(zip(bars, precision)):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
            f'{val:.1%}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    if i == 1:
        improvement = ((precision[1] - precision[0]) / precision[0]) * 100
        ax.text(bar.get_x() + bar.get_width()/2., height/2,
                f'+{improvement:.0f}%', ha='center', va='center', 
                fontsize=10, color='white', fontweight='bold', 
                bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
ax.grid(axis='y', alpha=0.3)

# 2. Recall Comparison
ax = axes[0, 1]
bars = ax.bar(models, recall, color=[color_default, color_tuned], alpha=0.8, edgecolor='black', linewidth=1.5)
ax.set_ylabel('Recall', fontsize=12, fontweight='bold')
ax.set_ylim(0, 1.1)
ax.set_title('Recall (Attack Detection Rate)', fontsize=12, fontweight='bold')
for i, (bar, val) in enumerate(zip(bars, recall)):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
            f'{val:.1%}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    if i == 1:
        ax.text(bar.get_x() + bar.get_width()/2., height/2,
                'MAINTAINED', ha='center', va='center', 
                fontsize=9, color='white', fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='blue', alpha=0.7))
ax.grid(axis='y', alpha=0.3)

# 3. F1-Score Comparison
ax = axes[0, 2]
bars = ax.bar(models, f1_score, color=[color_default, color_tuned], alpha=0.8, edgecolor='black', linewidth=1.5)
ax.set_ylabel('F1-Score', fontsize=12, fontweight='bold')
ax.set_ylim(0, 1.0)
ax.set_title('F1-Score (Harmonic Mean)', fontsize=12, fontweight='bold')
for i, (bar, val) in enumerate(zip(bars, f1_score)):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
            f'{val:.3f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    if i == 1:
        improvement = ((f1_score[1] - f1_score[0]) / f1_score[0]) * 100
        ax.text(bar.get_x() + bar.get_width()/2., height/2,
                f'+{improvement:.0f}%', ha='center', va='center', 
                fontsize=10, color='white', fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))
ax.grid(axis='y', alpha=0.3)

# 4. False Positives Comparison
ax = axes[1, 0]
bars = ax.bar(models, false_positives, color=[color_default, color_tuned], alpha=0.8, edgecolor='black', linewidth=1.5)
ax.set_ylabel('Count', fontsize=12, fontweight='bold')
ax.set_title('False Positives (Lower is Better)', fontsize=12, fontweight='bold')
for i, (bar, val) in enumerate(zip(bars, false_positives)):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 2,
            f'{int(val)}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    if i == 1:
        reduction = ((false_positives[0] - false_positives[1]) / false_positives[0]) * 100
        ax.text(bar.get_x() + bar.get_width()/2., height/2,
                f'−{reduction:.0f}%', ha='center', va='center', 
                fontsize=10, color='white', fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='darkgreen', alpha=0.7))
ax.grid(axis='y', alpha=0.3)

# 5. False Negatives Comparison
ax = axes[1, 1]
bars = ax.bar(models, false_negatives, color=[color_default, color_tuned], alpha=0.8, edgecolor='black', linewidth=1.5)
ax.set_ylabel('Count', fontsize=12, fontweight='bold')
ax.set_title('False Negatives (Missed Attacks)', fontsize=12, fontweight='bold')
ax.set_ylim(0, 5)
for i, (bar, val) in enumerate(zip(bars, false_negatives)):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.15,
            f'{int(val)}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    if i == 1:
        ax.text(bar.get_x() + bar.get_width()/2., 2.5,
                'NO ATTACKS MISSED', ha='center', va='center', 
                fontsize=9, color='white', fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='blue', alpha=0.7))
ax.grid(axis='y', alpha=0.3)

# 6. Summary Table
ax = axes[1, 2]
ax.axis('off')

summary_data = [
    ['Metric', 'Default', 'Tuned', 'Improvement'],
    ['Precision', '60.8%', '94.1%', '+77%'],
    ['F1-Score', '0.756', '0.970', '+28%'],
    ['False Pos.', '113', '11', '-90%'],
    ['False Neg.', '0', '0', 'SAME'],
    ['Recall', '100%', '100%', 'SAME'],
]

table = ax.table(cellText=summary_data, cellLoc='center', loc='center',
                colWidths=[0.25, 0.25, 0.25, 0.25])
table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 2.2)

# Style header row
for i in range(4):
    table[(0, i)].set_facecolor('#333333')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Style data rows
for i in range(1, len(summary_data)):
    for j in range(4):
        if i % 2 == 0:
            table[(i, j)].set_facecolor('#f0f0f0')
        if j == 3:  # Improvement column
            if '+' in str(summary_data[i][j]):
                table[(i, j)].set_facecolor('#c8e6c9')
                table[(i, j)].set_text_props(weight='bold', color='darkgreen')

plt.tight_layout()
plt.savefig('/app/output/threshold_tuning_comparison.png', dpi=300, bbox_inches='tight')
print("✅ Saved: /app/output/threshold_tuning_comparison.png")

# Print summary
print("\n" + "="*60)
print("THRESHOLD TUNING COMPARISON RESULTS")
print("="*60)
print(f"Precision:      {precision[0]:.1%} → {precision[1]:.1%}  (+{((precision[1]-precision[0])/precision[0])*100:.0f}%)")
print(f"Recall:         {recall[0]:.1%} → {recall[1]:.1%}  (MAINTAINED)")
print(f"F1-Score:       {f1_score[0]:.3f} → {f1_score[1]:.3f}  (+{((f1_score[1]-f1_score[0])/f1_score[0])*100:.0f}%)")
print(f"False Pos:      {int(false_positives[0])} → {int(false_positives[1])}  (-{((false_positives[0]-false_positives[1])/false_positives[0])*100:.0f}%)")
print(f"False Neg:      {int(false_negatives[0])} → {int(false_negatives[1])}  (NO ATTACKS MISSED)")
print("="*60)
