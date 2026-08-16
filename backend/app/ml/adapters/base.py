from abc import ABC, abstractmethod

from app.ml.contracts.dataset import MLDataset


class BaseAdapter(ABC):
    """
    Abstract interface for ML Data Adapters.
    Adapters are responsible for fetching raw normalized data from repositories
    and constructing a standardized MLDataset.
    """

    @abstractmethod
    async def fetch_dataset(self) -> MLDataset:
        """
        Fetches data, formats it into a contiguous time-series DataFrame,
        and returns an MLDataset.
        """
        pass
