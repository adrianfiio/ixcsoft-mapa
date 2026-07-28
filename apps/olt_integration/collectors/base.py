from abc import ABC, abstractmethod


class BaseOLTCollector(ABC):
    @abstractmethod
    def test_connection(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def collect_onus(self) -> list[dict]:
        raise NotImplementedError
