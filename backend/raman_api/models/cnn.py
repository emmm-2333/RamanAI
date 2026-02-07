import torch
import torch.nn as nn

class MultiTaskRamanCNN(nn.Module):
    def __init__(self, input_length=1801):
        super(MultiTaskRamanCNN, self).__init__()
        
        # Shared Backbone (Feature Extractor)
        self.features = nn.Sequential(
            # Block 1
            nn.Conv1d(1, 16, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm1d(16),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2, stride=2),
            
            # Block 2
            nn.Conv1d(16, 32, kernel_size=5, stride=2, padding=2),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2, stride=2),
            
            # Block 3
            nn.Conv1d(32, 64, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            
            # Global Average Pooling
            nn.AdaptiveAvgPool1d(1)
        )
        
        # Shared Dense Layer
        self.shared_fc = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.5)
        )
        
        # Task Heads
        # Main Task: Diagnosis (Benign/Malignant)
        self.head_diagnosis = nn.Linear(32, 1)
        
        # Aux Tasks
        self.head_er = nn.Linear(32, 1)
        self.head_pr = nn.Linear(32, 1)
        self.head_her2 = nn.Linear(32, 1)
        self.head_ki67 = nn.Linear(32, 1)

    def forward(self, x):
        # x shape: (Batch, 1, Length)
        feat = self.features(x)
        feat = feat.view(feat.size(0), -1) # Flatten (Batch, 64)
        
        shared = self.shared_fc(feat)
        
        # Outputs (Logits)
        out_diag = self.head_diagnosis(shared)
        out_er = self.head_er(shared)
        out_pr = self.head_pr(shared)
        out_her2 = self.head_her2(shared)
        out_ki67 = self.head_ki67(shared)
        
        return {
            'diagnosis': out_diag,
            'ER': out_er,
            'PR': out_pr,
            'HER2': out_her2,
            'Ki67': out_ki67
        }
