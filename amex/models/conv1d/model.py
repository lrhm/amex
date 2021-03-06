from argparse import Namespace
from .base_classification_model import BaseClassificationModel
import torch as t
from .modules.conv1d.conv1d import FATConv1dClassifier, AmexConv1DClassifier,DoubleConv1DClassifier
from .modules.lstm import LSTMClassifier

class Model(BaseClassificationModel):
    def __init__(self, params: Namespace):
        super().__init__(params)
        self.classifier = DoubleConv1DClassifier(params)
