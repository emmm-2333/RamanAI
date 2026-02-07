import torch
from torch.utils.data import Dataset
import numpy as np
import re

class MetadataParser:
    @staticmethod
    def parse_er_pr(value):
        """
        Parse ER/PR values.
        Returns: 1.0 (Positive), 0.0 (Negative), or -1.0 (Missing/Unknown)
        """
        if not value:
            return -1.0
        
        s = str(value).lower().strip()
        
        if s in ['nan', 'none', 'null', '']:
            return -1.0
            
        # Check for explicit negative
        if any(x in s for x in ['-', '阴성', 'negative', '阴性']):
            return 0.0
            
        # Check for explicit positive
        if any(x in s for x in ['+', '阳性', 'positive']):
            return 1.0
            
        # Percentage check (e.g., "80%")
        # Usually > 1% is considered positive for ER/PR
        match = re.search(r'(\d+)%', s)
        if match:
            try:
                val = float(match.group(1))
                return 1.0 if val >= 1.0 else 0.0
            except:
                pass
                
        return -1.0

    @staticmethod
    def parse_her2(value):
        """
        Parse HER2 values.
        Standard: 0, 1+ -> Negative (0)
                  2+ -> Equivocal (Treat as missing -1 or separate class? Let's treat as missing for binary)
                  3+ -> Positive (1)
        """
        if not value:
            return -1.0
            
        s = str(value).lower().strip()
        
        if s in ['nan', 'none', 'null', '']:
            return -1.0
            
        # Direct string matches
        if '3+' in s or 'positive' in s or '阳性' in s:
            return 1.0
        if '0' in s or '1+' in s or 'negative' in s or '阴性' in s:
            return 0.0
        if '2+' in s:
            return -1.0 # Equivocal, skip training on this unless FISH result provided
            
        return -1.0

    @staticmethod
    def parse_ki67(value):
        """
        Parse Ki67 values.
        Returns: 1.0 (High, >=14%), 0.0 (Low, <14%), -1.0 (Missing)
        Threshold 14% is common for St. Gallen consensus.
        """
        if not value:
            return -1.0
            
        s = str(value).lower().strip()
        
        if s in ['nan', 'none', 'null', '']:
            return -1.0
            
        # Extract number
        match = re.search(r'(\d+)', s)
        if match:
            try:
                val = float(match.group(1))
                return 1.0 if val >= 14.0 else 0.0
            except:
                pass
                
        return -1.0

class RamanDataset(Dataset):
    def __init__(self, X_spectra, y_diagnosis, metadata_list=None):
        """
        :param X_spectra: List or array of spectral intensities
        :param y_diagnosis: List or array of binary diagnosis (0=Benign, 1=Malignant)
        :param metadata_list: List of dicts containing {'ER':..., 'PR':..., 'HER2':..., 'Ki67':...}
        """
        self.X = torch.tensor(X_spectra, dtype=torch.float32).unsqueeze(1) # Add channel dim: (N, 1, L)
        self.y = torch.tensor(y_diagnosis, dtype=torch.float32)
        
        # Parse metadata targets
        self.targets_aux = []
        if metadata_list:
            for meta in metadata_list:
                er = MetadataParser.parse_er_pr(meta.get('ER'))
                pr = MetadataParser.parse_er_pr(meta.get('PR'))
                her2 = MetadataParser.parse_her2(meta.get('HER2'))
                ki67 = MetadataParser.parse_ki67(meta.get('Ki67'))
                self.targets_aux.append([er, pr, her2, ki67])
        else:
            # If no metadata, fill with -1
            self.targets_aux = [[-1.0]*4 for _ in range(len(X_spectra))]
            
        self.targets_aux = torch.tensor(self.targets_aux, dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        # Return: spectrum, diagnosis_label, aux_labels (ER, PR, HER2, Ki67)
        return self.X[idx], self.y[idx], self.targets_aux[idx]
