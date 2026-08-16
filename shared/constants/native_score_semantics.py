from enum import Enum

class NativeScoreSemanticsEnum(str, Enum):
    probability_of_positive_class = "probability_of_positive_class"
    probability_of_negative_class = "probability_of_negative_class"
    distance_score = "distance_score"
    anomaly_score = "anomaly_score"
