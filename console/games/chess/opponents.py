"""Who you play against: the built-in engine, Stockfish, or a Hermes model.

An opponent turns a position into a move. ``choose`` blocks (a model call can
take seconds), so the game runs it on a worker thread.
"""

from __future__ import annotations

import os
import random
import re

from . import engine
from .rules import Board, uci

# The Hermes plugin hands over ``ctx.llm`` here when it loads. Standalone runs have none.
_LLM = None


def set_llm(llm) -> None:
    global _LLM
    _LLM = llm


def llm_available() -> bool:
    return _LLM is not None


class Opponent:
    label = "Opponent"

    def choose(self, board: Board, history: list[str]) -> tuple[int, str]:
        """Return ``(move, note)``; ``note`` is shown to the player (may be empty)."""
        raise NotImplementedError

    def close(self) -> None:
        pass


class EngineOpponent(Opponent):
    def __init__(self, level_index: int) -> None:
        self.level = engine.LEVELS[level_index]
        self.label = f"Engine ({self.level.name})"
        self.rng = random.Random()

    def choose(self, board, history):
        return engine.best_move(board, self.level, self.rng), ""


class StockfishOpponent(Opponent):
    # Stockfish "Skill Level" 0..20 and thinking time for each of our four strengths
    SKILL = [(1, 100), (6, 250), (12, 600), (20, 1500)]

    def __init__(self, level_index: int) -> None:
        path = engine.find_stockfish()
        if path is None:
            raise RuntimeError("Stockfish not found")
        self.sf = engine.Stockfish(path)
        self.skill, self.ms = self.SKILL[level_index]
        self.label = f"Stockfish ({engine.LEVELS[level_index].name})"

    def choose(self, board, history):
        m = self.sf.best_move(board, self.skill, self.ms)
        if m is None:
            raise RuntimeError("Stockfish returned no move")
        return m, ""

    def close(self) -> None:
        self.sf.close()


SYSTEM = (
    "You are a strong chess player. You will be given the current position and the complete list of legal "
    "moves. Choose the best move for the side to move. Reply with exactly one move taken from the list, in "
    "the same notation, and nothing else."
)


def _history_text(history: list[str]) -> str:
    out = []
    for i, san in enumerate(history):
        out.append(f"{i // 2 + 1}. {san}" if i % 2 == 0 else san)
    return " ".join(out) or "(game start)"


def _extract(board: Board, reply: str) -> int | None:
    """First token of the reply that is a legal move (SAN or UCI); models like to add words."""
    text = reply.strip()
    m = board.find_move(text.splitlines()[0]) if text else None
    if m is not None:
        return m
    for tok in re.findall(r"[A-Za-z0-9=+#\-]+", text):
        m = board.find_move(tok)
        if m is not None:
            return m
    return None


class ModelOpponent(Opponent):
    """Asks the model Hermes is running, through ``ctx.llm``."""

    ATTEMPTS = 3

    def __init__(self, fallback_level: int = 2) -> None:
        if _LLM is None:
            raise RuntimeError("no Hermes model available (open Console from Hermes)")
        self.label = "Hermes model"
        self.fallback = EngineOpponent(fallback_level)

    def _call(self, messages) -> str:
        kwargs = {"max_tokens": 600, "timeout": 120, "purpose": "console chess move"}
        model = os.environ.get("CONSOLE_CHESS_MODEL")
        provider = os.environ.get("CONSOLE_CHESS_PROVIDER")
        if model:
            kwargs["model"] = model
        if provider:
            kwargs["provider"] = provider
        result = _LLM.complete(messages, **kwargs)
        self.label = f"Hermes model ({result.model})"
        return result.text or ""

    def choose(self, board, history):
        legal = board.legal_moves()
        san = [board.san(m, legal) for m in legal]
        side = "White" if board.turn > 0 else "Black"
        prompt = (
            f"Position (FEN): {board.fen()}\n"
            f"You play {side}.\n"
            f"Moves so far: {_history_text(history)}\n"
            f"Legal moves: {', '.join(san)}\n"
            "Your move:"
        )
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
        for attempt in range(self.ATTEMPTS):
            try:
                reply = self._call(messages)
            except Exception as exc:
                name = type(exc).__name__
                hint = ""
                if "Trust" in name:
                    hint = " (to pick a model, allow it under plugins.entries.console.llm in config.yaml)"
                move, _ = self.fallback.choose(board, history)
                return move, f"Model unavailable ({name}){hint}; the engine moved instead."
            move = _extract(board, reply)
            if move is not None:
                return move, ""
            messages.append({"role": "assistant", "content": reply[:200]})
            messages.append({"role": "user", "content": f"That is not a legal move. Legal moves: {', '.join(san)}. Reply with one of them."})
        move, _ = self.fallback.choose(board, history)
        return move, "The model kept answering with illegal moves; the engine moved for it."


def available() -> list[tuple[str, str]]:
    """(key, menu text) for each opponent that can be used right now."""
    out = [("engine", "Built-in engine")]
    if engine.find_stockfish():
        out.append(("stockfish", "Stockfish"))
    if llm_available():
        out.append(("model", "Hermes model"))
    return out


def make(kind: str, level_index: int) -> Opponent:
    if kind == "stockfish":
        return StockfishOpponent(level_index)
    if kind == "model":
        return ModelOpponent()
    return EngineOpponent(level_index)


__all__ = ["Opponent", "available", "make", "set_llm", "llm_available", "uci"]
