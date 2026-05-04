from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .base import BaseInterpreter, ExecutionResult
from .utils import InputBuffer, coerce_input


POSITIVE_ADJECTIVES = {
    "brave": 2,
    "honest": 1,
    "noble": 2,
    "fair": 1,
    "sweet": 1,
    "gentle": 1,
}
NEGATIVE_ADJECTIVES = {
    "cowardly": -2,
    "ugly": -1,
    "vile": -2,
    "cruel": -1,
    "horrible": -2,
    "rotten": -2,
}
NOUN_VALUES = {
    "hero": 10,
    "king": 20,
    "queen": 18,
    "soldier": 8,
    "villain": -12,
    "rat": -2,
    "pig": -3,
    "flower": 1,
    "sun": 5,
    "ghost": -5,
    "cat": 3,
    "dog": 4,
}


@dataclass
class Command:
    speaker: str
    kind: str
    argument: Optional[str] = None


@dataclass
class Scene:
    name: str
    commands: List[Command] = field(default_factory=list)
    directions: List[Tuple[str, List[str]]] = field(default_factory=list)  # (type, names)


@dataclass
class Script:
    characters: List[str]
    scenes: List[Scene]
    scene_lookup: Dict[str, int]


class CharacterState:
    def __init__(self, name: str):
        self.name = name
        self.stack: List[int] = []

    def push(self, value: int) -> None:
        self.stack.append(int(value))

    def assign(self, value: int) -> None:
        if self.stack:
            self.stack[-1] = int(value)
        else:
            self.stack.append(int(value))

    def pop(self) -> int:
        if not self.stack:
            raise RuntimeError(f"{self.name} has nothing to recall")
        return self.stack.pop()

    def peek(self) -> int:
        if not self.stack:
            raise RuntimeError(f"{self.name} has no memories")
        return self.stack[-1]


class ShakespeareInterpreter(BaseInterpreter):
    """Practical subset of the Shakespeare Programming Language."""

    language_name = "Shakespeare"

    def _execute(self, code: str, stdin: str | bytes | None) -> ExecutionResult:
        try:
            script = self._parse_script(code)
        except ValueError as exc:
            return ExecutionResult(
                stdout="",
                stderr=f"SPL compile error: {exc}",
                exit_code=1,
                error_type="compile_error",
            )

        characters = {name: CharacterState(name) for name in script.characters}
        stage: List[str] = []
        stdout_chars: List[str] = []
        input_stream: InputBuffer = coerce_input(stdin)
        scene_index = 0
        trace_steps = 0

        while 0 <= scene_index < len(script.scenes):
            scene = script.scenes[scene_index]
            idx = 0
            while idx < len(scene.commands):
                command = scene.commands[idx]
                if command.kind.startswith("stage_"):
                    self._execute_stage_direction(command, stage)
                    idx += 1
                    continue
                speaker = command.speaker
                if speaker not in stage:
                    return ExecutionResult(
                        stdout="".join(stdout_chars),
                        stderr=f"SPL runtime error: {speaker} speaks while offstage",
                        exit_code=1,
                        error_type="runtime_error",
                        trace=self._trace(trace_steps, speaker, stage),
                    )
                state = characters[speaker]
                try:
                    jump = self._execute_command(
                        command,
                        state,
                        stage,
                        characters,
                        script.scene_lookup,
                        stdout_chars,
                        input_stream,
                    )
                except RuntimeError as exc:
                    return ExecutionResult(
                        stdout="".join(stdout_chars),
                        stderr=f"SPL runtime error: {exc}",
                        exit_code=1,
                        error_type="runtime_error",
                        trace=self._trace(trace_steps, speaker, stage),
                    )

                trace_steps += 1
                if isinstance(jump, str):
                    if jump not in script.scene_lookup:
                        return ExecutionResult(
                            stdout="".join(stdout_chars),
                            stderr=f"SPL runtime error: unknown scene '{jump}'",
                            exit_code=1,
                            error_type="runtime_error",
                        )
                    scene_index = script.scene_lookup[jump]
                    break
                idx += 1
            else:
                scene_index += 1
                continue
            continue  # jumped to a new scene

        return ExecutionResult(
            stdout="".join(stdout_chars),
            stderr="",
            exit_code=0,
            error_type="ok",
            trace=self._trace(trace_steps, None, stage),
        )

    def _parse_script(self, code: str) -> Script:
        lines = [line.rstrip() for line in code.splitlines()]
        characters: List[str] = []
        scenes: List[Scene] = []
        scene_lookup: Dict[str, int] = {}
        current_scene: Optional[Scene] = None
        current_speaker: Optional[str] = None
        stage: List[str] = []

        parsing_characters = True
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            if parsing_characters and "," in line and ":" not in line:
                name = line.split(",")[0].strip()
                if name:
                    characters.append(name)
                continue
            parsing_characters = False

            lower = line.lower()
            if lower.startswith("act "):
                continue
            if lower.startswith("scene "):
                scene_name = line.split(":", 1)[0].strip()
                current_scene = Scene(name=scene_name)
                scenes.append(current_scene)
                scene_lookup[scene_name.lower()] = len(scenes) - 1
                current_speaker = None
                continue
            if lower.startswith("enter "):
                if current_scene is None:
                    raise ValueError("Enter directive outside scene")
                names = self._parse_character_list(line[6:])
                for name in names:
                    if name not in characters:
                        characters.append(name)
                current_scene.commands.append(Command(speaker="Narrator", kind="stage_enter", argument=", ".join(names)))
                continue
            if lower.startswith("exit "):
                names = self._parse_character_list(line[5:])
                for name in names:
                    if name not in characters:
                        characters.append(name)
                if current_scene:
                    current_scene.commands.append(Command(speaker="Narrator", kind="stage_exit", argument=", ".join(names)))
                continue
            if lower.startswith("exeunt"):
                if current_scene:
                    current_scene.commands.append(Command(speaker="Narrator", kind="stage_clear"))
                continue

            if ":" in line:
                speaker = line.split(":", 1)[0].strip()
                if speaker not in characters:
                    characters.append(speaker)
                current_speaker = speaker
                line = line.split(":", 1)[1].strip()

            if current_scene is None:
                continue
            if not current_speaker:
                raise ValueError("Speech without speaker")
            sentences = [s.strip() for s in re.split(r"[.!?]", line) if s.strip()]
            for sentence in sentences:
                command = self._parse_sentence(current_speaker, sentence)
                current_scene.commands.append(command)

        if not scenes:
            raise ValueError("No scenes defined")
        return Script(characters=characters or ["Narrator"], scenes=scenes, scene_lookup=scene_lookup)

    def _parse_sentence(self, speaker: str, sentence: str) -> Command:
        lowered = sentence.lower()
        if lowered.startswith("remember "):
            return Command(speaker, "remember", sentence[9:].strip())
        if lowered.startswith("recall"):
            return Command(speaker, "recall")
        if lowered.startswith("you are"):
            return Command(speaker, "assign", sentence[7:].strip())
        if lowered.startswith("speak your mind"):
            return Command(speaker, "speak_char")
        if lowered.startswith("open your heart"):
            return Command(speaker, "speak_number")
        if lowered.startswith("listen to your heart"):
            return Command(speaker, "input_number")
        if lowered.startswith("listen to your head"):
            return Command(speaker, "input_char")
        if lowered.startswith("if so"):
            target = self._extract_scene(sentence)
            return Command(speaker, "jump_positive", target)
        if lowered.startswith("if not"):
            target = self._extract_scene(sentence)
            return Command(speaker, "jump_nonpositive", target)
        if lowered.startswith("let us proceed"):
            target = self._extract_scene(sentence)
            return Command(speaker, "jump", target)
        raise ValueError(f"Unsupported sentence: '{sentence}'")

    def _extract_scene(self, sentence: str) -> str:
        match = re.search(r"scene\s+([A-Za-z0-9 ]+)", sentence, re.IGNORECASE)
        if not match:
            raise ValueError("Scene reference missing")
        return f"Scene {match.group(1).strip()}"

    def _parse_character_list(self, text: str) -> List[str]:
        text = text.strip().rstrip(".")
        parts = re.split(r",|and", text)
        return [part.strip() for part in parts if part.strip()]

    def _execute_command(
        self,
        command: Command,
        state: CharacterState,
        stage: List[str],
        characters: Dict[str, CharacterState],
        scene_lookup: Dict[str, int],
        stdout_chars: List[str],
        input_stream: InputBuffer,
    ) -> Optional[str]:
        kind = command.kind
        if kind == "remember":
            value = self._evaluate_expression(command.argument or "", state)
            state.push(value)
        elif kind == "assign":
            value = self._evaluate_expression(command.argument or "", state)
            state.assign(value)
        elif kind == "recall":
            state.pop()
        elif kind == "speak_char":
            stdout_chars.append(chr(state.peek() % 256))
        elif kind == "speak_number":
            stdout_chars.append(str(state.peek()))
        elif kind == "input_number":
            number = input_stream.read_number()
            if number is None:
                raise RuntimeError("numeric input exhausted")
            state.push(number)
        elif kind == "input_char":
            char = input_stream.read_char()
            if char is None:
                raise RuntimeError("character input exhausted")
            state.push(ord(char))
        elif kind == "jump_positive":
            if state.peek() > 0:
                return (command.argument or "").lower()
        elif kind == "jump_nonpositive":
            if state.peek() <= 0:
                return (command.argument or "").lower()
        elif kind == "jump":
            return (command.argument or "").lower()
        return None

    def _execute_stage_direction(self, command: Command, stage: List[str]) -> None:
        names = []
        if command.argument:
            names = [name.strip() for name in command.argument.split(",") if name.strip()]
        if command.kind == "stage_enter":
            for name in names:
                if name not in stage:
                    stage.append(name)
        elif command.kind == "stage_exit":
            for name in names:
                if name in stage:
                    stage.remove(name)
        elif command.kind == "stage_clear":
            stage.clear()

    def _evaluate_expression(self, text: str, state: CharacterState) -> int:
        expr = text.strip().lower()
        if not expr:
            raise RuntimeError("empty expression")
        if expr.startswith("as "):
            parts = expr.split(" as ", 2)
            if len(parts) == 3:
                expr = parts[2]
        if expr == "nothing":
            return 0
        if expr == "yourself":
            return state.peek()
        if re.fullmatch(r"-?\d+", expr):
            return int(expr)
        if expr.startswith("the sum of "):
            left, right = self._split_pair(expr[11:], "and")
            return self._evaluate_expression(left, state) + self._evaluate_expression(right, state)
        if expr.startswith("the difference between "):
            left, right = self._split_pair(expr[23:], "and")
            return self._evaluate_expression(left, state) - self._evaluate_expression(right, state)
        if expr.startswith("the product of "):
            left, right = self._split_pair(expr[15:], "and")
            return self._evaluate_expression(left, state) * self._evaluate_expression(right, state)
        if expr.startswith("the quotient between "):
            left, right = self._split_pair(expr[21:], "and")
            denominator = self._evaluate_expression(right, state)
            if denominator == 0:
                raise RuntimeError("division by zero")
            return self._evaluate_expression(left, state) // denominator
        return self._value_from_phrase(expr)

    def _split_pair(self, text: str, keyword: str) -> Tuple[str, str]:
        parts = text.split(f" {keyword} ", 1)
        if len(parts) != 2:
            raise RuntimeError(f"could not split expression around '{keyword}'")
        return parts[0].strip(), parts[1].strip()

    def _value_from_phrase(self, phrase: str) -> int:
        tokens = [tok for tok in re.split(r"[ -]", phrase) if tok not in {"a", "an", "the"}]
        noun = None
        for tok in reversed(tokens):
            if tok in NOUN_VALUES:
                noun = tok
                break
        if not noun:
            raise RuntimeError(f"unknown noun in phrase '{phrase}'")
        adjective_score = sum(POSITIVE_ADJECTIVES.get(tok, 0) + NEGATIVE_ADJECTIVES.get(tok, 0) for tok in tokens if tok != noun)
        base = NOUN_VALUES[noun]
        return base + adjective_score

    def _trace(self, steps: int, speaker: Optional[str], stage: List[str]) -> dict:
        return {
            "steps": steps,
            "last_speaker": speaker,
            "stage": list(stage),
        }
