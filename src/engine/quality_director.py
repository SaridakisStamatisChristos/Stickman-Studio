"""Content-first narrative direction for offline Stickman Studio.

The original inbuilt director is a motivational-domain template system, not a
general fiction writer. This module adds an explicit intent contract and a
deterministic fiction fallback, with optional local Ollama for open-ended work.
It never calls a remote LLM and never invents factual explanations when no
knowledge model is available.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

VALID_MODES = {"auto", "fiction", "explanation", "motivation", "dialogue"}
_STORY_VERBS = re.compile(
    r"\b(discovers?|finds?|encounters?|hears?|follows?|escapes?|meets?|"
    r"wakes?|awakens?|journeys?|returns?|opens?|loses?|rescues?|searches?)\b",
    re.I,
)
_STORY_CUES = re.compile(
    r"\b(story|fiction|once upon|a lonely|an abandoned|a mysterious|a lost|"
    r"a young|a forgotten|short film|character|novel|narrative)\b",
    re.I,
)
_EXPLANATION = re.compile(r"^\s*(why|how|what|explain|teach|describe)\b", re.I)
_STOP = {"a", "an", "the", "why", "how", "what", "is", "do", "does", "from", "of", "to"}


def content_mode_for(topic: str, requested: str = "auto") -> str:
    requested = str(requested or "auto").strip().lower()
    if requested not in VALID_MODES:
        raise ValueError(f"Unsupported content_mode: {requested}")
    if requested != "auto":
        return requested
    topic = (topic or "").strip()
    if _STORY_CUES.search(topic) or (
        _STORY_VERBS.search(topic) and not _EXPLANATION.search(topic)
    ):
        return "fiction"
    if _EXPLANATION.search(topic) or topic.endswith("?"):
        return "explanation"
    return "motivation"


@dataclass(frozen=True)
class NarrativePlan:
    topic: str
    mode: str
    seed: int
    premise: str
    character: str
    incident: str
    setting: str
    beats: tuple[str, ...]


def stable_seed(topic: str) -> int:
    return int(hashlib.sha256((topic or "").strip().lower().encode()).hexdigest()[:8], 16)


def plan_narrative(topic: str, mode: str = "auto", seed: int | None = None) -> NarrativePlan:
    topic = re.sub(r"\s+", " ", (topic or "").strip()).strip(".?!")
    mode = content_mode_for(topic, mode)
    seed = stable_seed(topic) if seed is None else int(seed)
    if mode != "fiction":
        beats = (
            f"Introduce the specific subject: {topic}.",
            f"Identify the core question about {topic}.",
            "Explore the mechanism or competing perspectives.",
            "Give a concrete example, if verifiable.",
            "Close with a useful and bounded takeaway.",
        )
        return NarrativePlan(topic, mode, seed, topic, "", "", "", beats)

    match = re.match(
        r"^(?:a|an|the)\s+(.+?)\s+(discovers?|finds?|encounters?|hears?|"
        r"follows?|escapes?|meets?|wakes?|awakens?|journeys?|returns?|"
        r"opens?|loses?|rescues?|searches?)\s+(.+)$", topic, re.I,
    )
    if match:
        character = re.sub(r"\s+", " ", match.group(1)).strip()
        event = match.group(2).lower()
        obj = match.group(3).rstrip(".")
        incident = f"{event} {obj}"
    else:
        character = "traveler"
        incident = topic[0].lower() + topic[1:] if topic else "an unexpected discovery"
    setting = (
        "an abandoned city" if re.search(r"robot|city|signal", topic, re.I)
        else "a quiet, unfamiliar place"
    )
    lead = f"the {character}" if character != "traveler" else "the traveler"
    beats = (
        f"Establish {lead} in {setting}.",
        f"Show {lead} {incident}.",
        f"Make the discovery personally consequential to {lead}.",
        "Reveal an unexpected complication without switching subjects.",
        f"Give {lead} a meaningful decision.",
        "End on a concrete changed situation rather than advice.",
    )
    return NarrativePlan(topic, mode, seed, topic, lead, incident, setting, beats)


def _local_model_script(plan: NarrativePlan, duration: int, llm_manager) -> str:
    if not llm_manager or not hasattr(llm_manager, "generate"):
        return ""
    if hasattr(llm_manager, "check_ollama_running") and not llm_manager.check_ollama_running():
        return ""
    words = max(35, min(260, int(duration * 2.35)))
    prompt = (
        "You are a cinematic short-script author. Write only narration, no markdown. "
        f"Intent: {plan.mode}. Topic: {plan.topic}. Approximate words: {words}. "
        "Honor the exact premise, character and setting. No generic coaching, "
        "irrelevant software tutorials or motivational clichés. "
        "For factual explanations, avoid invented assertions and fabricated dates. "
        "Keep an understandable sequence and an actual ending. "
        "Required structural beats: " + " | ".join(plan.beats)
    )
    text = (llm_manager.generate(prompt, max_tokens=min(500, words * 3), temperature=0.55) or "").strip()
    if not 25 <= len(text.split()) <= max(400, 2 * words):
        return ""
    if plan.mode == "fiction" and re.search(
        r"\b(developer|debugging|compiler|codebase|software engineer)\b", text, re.I
    ) and not re.search(r"\b(code|developer|programmer)\b", plan.topic, re.I):
        return ""
    return text


def _deterministic_fiction(plan: NarrativePlan, duration: int) -> str:
    hero = plan.character
    event = plan.incident
    if hero == "the traveler":
        intro = f"At the edge of {plan.setting}, the traveler faced a strange possibility: {plan.topic}."
        trigger = "A small sign appeared, too deliberate to be an accident."
    else:
        intro = f"In {plan.setting}, {hero} moved through the silence, searching for a reason to continue."
        # Inflect only the most common present-tense verbs to avoid awkward narration.
        transformed = re.sub(
            r"^(discovers|finds|encounters|hears|follows|escapes|meets|opens|loses|rescues|searches)\b",
            lambda m: {"discovers":"discovered","finds":"found","encounters":"encountered",
                       "hears":"heard","follows":"followed","escapes":"escaped","meets":"met",
                       "opens":"opened","loses":"lost","rescues":"rescued","searches":"searched"}[m.group(1)],
            event, count=1
        )
        trigger = f"Then {hero} {transformed}."
    middle = (
        "A faint glow revealed a path that no one had walked for years.",
        f"{hero.capitalize()} reached toward it, uncertain whether to follow or turn back.",
        "For an instant, the world seemed to hold its breath.",
        "The signal changed. Someone, somewhere, was answering.",
        f"Instead of retreating, {hero} stepped forward.",
        "The darkness had not disappeared, but now it held a direction."
    )
    sentences = [intro, trigger] + list(middle)
    count = max(32, round(duration * 2.0))
    out = [sentences[0], sentences[1]]
    for sent in sentences[2:-1]:
        if len(" ".join(out).split()) >= count - 14:
            break
        out.append(sent)
    out.append(sentences[-1])
    return " ".join(out)


def generate_quality_script(topic: str, duration: int = 30, mode: str = "auto",
                            llm_manager=None, seed: int | None = None) -> tuple[str, NarrativePlan]:
    plan = plan_narrative(topic, mode, seed)
    generated = _local_model_script(plan, duration, llm_manager)
    if generated:
        return generated, plan
    if plan.mode == "fiction":
        return _deterministic_fiction(plan, duration), plan
    # Existing inbuilt templates are retained for motivation only. For factual
    # subjects without a local model, do not pretend to give an expert lecture.
    if plan.mode == "explanation":
        return (
            f"Here is the question: {plan.topic}. "
            "A useful explanation begins by identifying the actual mechanism, "
            "the conditions under which it works, and the evidence for it. "
            f"To understand {plan.topic}, we should distinguish observations "
            "from assumptions and check specific examples against reliable sources. "
            "Without verified subject knowledge, a polished animation is not a substitute for an accurate answer."
        ), plan
    from engine.inbuilt_ai_director import InbuiltAIDirector
    return InbuiltAIDirector.generate_script(topic, duration=duration,
                                            seed=plan.seed), plan
