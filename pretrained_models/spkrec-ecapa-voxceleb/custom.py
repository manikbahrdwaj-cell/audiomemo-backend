# Minimal ECAPA-TDNN custom module for SpeechBrain
from speechbrain.lobes.models.ECAPA_TDNN import ECAPA_TDNN, Classifier
import speechbrain.lobes.features as features
from speechbrain.processing.features import InputNormalization
from speechbrain.dataio.encoder import CategoricalEncoder
from speechbrain.lobes.models.ECAPA_TDNN import ECAPA_TDNN as EcapaTdnn
from speechbrain.utils.parameter_transfer import Pretrainer

__all__ = ["ECAPA_TDNN", "Classifier", "EcapaTdnn", "InputNormalization", "CategoricalEncoder"]
