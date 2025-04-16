# Overall score calculation


# Install matplotlib if not already installed
# !pip install matplotlib seaborn scikit-learn

import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, cohen_kappa_score


# Root Cause Identification
root_rater1 = ['root_precise'] * 117 + ['root_partial'] * 102 + ['root_missing'] * 31
root_rater2 = ['root_precise'] * 131 + ['root_partial'] * 88 + ['root_missing'] * 31

# Fix Suggestion
fix_rater1 = ['fix_correct'] * 81 + ['fix_alternative'] * 109 + ['fix_preventive'] * 22 + ['fix_missing'] * 38
fix_rater2 = ['fix_correct'] * 91 + ['fix_alternative'] * 88 + ['fix_preventive'] * 33 + ['fix_missing'] * 38

# Problem Location Identification
loc_rater1 = ['loc_precise'] * 186 + ['loc_partial'] * 45 + ['loc_missing'] * 19
loc_rater2 = ['loc_precise'] * 186 + ['loc_partial'] * 47 + ['loc_missing'] * 17

# Wrong Information?
wrong_rater1 = ['wrong_yes'] * 0 + ['wrong_no'] * 250
wrong_rater2 = ['wrong_yes'] * 0 + ['wrong_no'] * 250

# Overall Data Labels -----------------------------------------------------------------
rater1 = root_rater1 + fix_rater1 + loc_rater1 + wrong_rater1
rater2 = root_rater2 + fix_rater2 + loc_rater2 + wrong_rater2
print('rater1 overall:', len(rater1))
print('rater2 overall:', len(rater2))
print('rater1 overall:', rater1)
print('rater2 overall:', rater2)
# Overall Data Labels -----------------------------------------------------------------


# Calculate confusion matrix
labels = ['root_precise', 'root_partial', 'root_missing', 'fix_correct', 'fix_alternative', 'fix_preventive', 'fix_missing', 'loc_precise', 'loc_partial', 'loc_missing', 'wrong_yes', 'wrong_no']
cm = confusion_matrix(rater1, rater2, labels=labels)

# Display confusion matrix using seaborn for color
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=labels, yticklabels=labels)
plt.title('Confusion Matrix Between Rater 1 and Rater 2')
plt.xlabel('Rater 2')
plt.ylabel('Rater 1')
plt.show()

# Calculate and print Cohen's Kappa
kappa = cohen_kappa_score(rater1, rater2)
print("Cohen's Kappa Score:", round(kappa, 4))
