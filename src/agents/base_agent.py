from __future__ import annotations

from abc import ABC, abstractmethod


class BaseAgent(ABC):
    @abstractmethod
    def run(self, **kwargs):
        "Execute the agent's main behavior."
