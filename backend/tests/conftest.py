import pytest

from app import config
from app.antonyms import AntonymDict
from app.pipeline import Resources


@pytest.fixture(scope="session")
def antonyms() -> AntonymDict:
    return AntonymDict.load(config.ANTONYMS_CSV)


@pytest.fixture(scope="session")
def resources(antonyms) -> Resources:
    return Resources(antonyms=antonyms)
