from abc import ACB, abstractmethod
from typing import List

class Formatter:
    """
    
    """

    @abstractmethod
    def format(image_paths: List[str], text: List[str]) -> str:
        """
        Formats a pdf into text
        Params:
            paths to images
            text to put in report
        Returns:
            path to pdf
        """