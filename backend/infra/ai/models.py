from __future__ import annotations

from sklearn.compose import TransformedTargetRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import SEED


def build_regressor(seed: int = SEED) -> TransformedTargetRegressor:
    return TransformedTargetRegressor(
        regressor=make_pipeline(
            StandardScaler(),
            MLPRegressor(
                hidden_layer_sizes=(128, 128),
                alpha=1e-4,
                batch_size=512,  # pyright: ignore[reportArgumentType]
                learning_rate_init=1e-3,
                max_iter=300,
                early_stopping=True,
                random_state=seed,
            ),
        ),
        transformer=StandardScaler(),
    )


def build_classifier(seed: int = SEED) -> Pipeline:
    return make_pipeline(
        StandardScaler(),
        MLPClassifier(
            hidden_layer_sizes=(64, 32),
            alpha=1e-4,
            batch_size=512,  # pyright: ignore[reportArgumentType]
            learning_rate_init=1e-3,
            max_iter=300,
            early_stopping=True,
            random_state=seed,
        ),
    )
