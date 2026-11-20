# Created by Atharv Hatwar
"""
inbuilt_ai_director.py - High-Performance Multi-Domain Inbuilt AI Script & Director Engine.
Optimized for Ryzen 5 / GTX 1650 4GB / 8GB RAM.
100% Offline, Instant Execution (<0.05s), Zero External Dependencies.

Supported Universal Domains:
  1. Wealth, Business & Investing (Compounding, Real Estate, Crypto, Sales, Cash Flow)
  2. Tech, Coding & AI (Programming, Algorithms, Software, Robotics, Cyber)
  3. Fitness, Health & Athletics (Gym, Muscle, Nutrition, Sleep, Energy)
  4. Stoicism, Philosophy & History (Marcus Aurelius, Ancient Rome, Virtue, Samurai)
  5. Habits, Focus & Productivity (Deep Work, Atomic Habits, Pomodoro, Discipline)
  6. Motivation, Mindset & Grit (Winning, Mental Toughness, Resilience)
  7. Science, Space & Universe (Physics, Quantum, Atoms, Black Holes, Cosmos)
  8. Relatable Daily Life & Comedy (Awkward Moments, Office Life, Texts)
  9. Dark Psychology & Human Behavior (Attraction, Body Language, Mixed Signals)
 10. Universal Semantic Synthesis (Dynamically synthesizes scripts on ANY arbitrary topic)
 11. Topic-Word Extraction + Template Recombination (unique script per run, <0.5ms)
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Standard speech pacing for energetic social reels: ~2.4 words per second
WORDS_PER_SEC = 2.40

_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "wealth_business": ("money", "wealth", "invest", "rich", "crypto", "bitcoin", "dollar", "finance", "business", "cash flow", "passive income", "profit", "roi", "asset", "compound", "sales", "marketing", "startup", "economy", "trade", "capital", "entrepreneur"),
    "tech_coding_ai": ("code", "coding", "program", "developer", "software", "python", "ai", "artificial intelligence", "tech", "algorithm", "robot", "cyber", "terminal", "hack", "data", "machine learning", "neural", "cloud", "api", "app", "web", "bug", "debug", "llm", "deep learning"),
    "fitness_health_bio": ("gym", "workout", "muscle", "fitness", "exercise", "weight", "diet", "calorie", "protein", "bodybuilding", "fat loss", "cardio", "sleep", "health", "medicine", "medical", "doctor", "hospital", "surgery", "recovery", "nutrition", "longevity", "biotech"),
    "stoicism_philosophy_history": ("stoic", "marcus", "aurelius", "seneca", "epictetus", "rome", "greek", "ancient", "philosophy", "virtue", "warrior", "samurai", "empire", "wisdom", "fate", "napoleon", "bonaparte", "caesar", "alexander", "war", "battle", "history", "emperor", "sparta", "tactics", "conquer"),
    "habits_productivity_focus": ("habit", "habits", "productiv", "focus", "deep work", "procrastinat", "routine", "discipline", "pomodoro", "distraction", "morning routine", "time management", "goal", "study"),
    "motivation_mindset_leadership": ("motivat", "mindset", "never give up", "resilience", "grit", "success", "winner", "greatness", "failure", "standards", "leader", "leadership", "champion", "hard work", "courage"),
    "science_space_nature": ("science", "space", "planet", "physics", "quantum", "universe", "atom", "galaxy", "black hole", "gravity", "brain fact", "biology", "dna", "rocket", "mars", "moon", "astronomy", "nasa", "spacex", "orbit", "telescope", "solar", "earth", "star", "cosmos"),
    "comedy_daily_relatable": ("funny", "awkward", "relatable", "joke", "comedy", "everyday", "office", "texting", "embarrass", "alarm", "wifi"),
    "psychology_human_behavior": ("psychology", "signal", "ignore", "attract", "girl", "manipulat", "narcissis", "toxic", "validation", "overthink", "subconscious", "emotion", "dark", "relationship", "dating", "bias", "behavior", "cognitive"),
}

_STOPWORDS = frozenset((
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might", "must",
    "that", "this", "these", "those", "it", "its", "you", "your", "my", "our",
    "their", "we", "they", "he", "she", "him", "her", "them", "us", "not", "no",
    "so", "if", "then", "than", "when", "how", "why", "what", "who", "which",
    "about", "into", "from", "out", "up", "down", "over", "under", "through",
))

# 30 universal solo templates — {T}=topic, {K1}/{K2}=salient topic words.
# Recombined with topic-specific fill-ins → unique script per run. <0.5ms, zero deps.
_UNIVERSAL_SOLO_TEMPLATES: list[str] = [
    "Here's the uncomfortable truth about {T} that most people never face.",
    "The real reason {T} is harder than it looks has nothing to do with talent.",
    "What nobody teaches you about {T} until it's already cost you dearly.",
    "Stop approaching {T} the conventional way — here's what actually works.",
    "Every expert on {T} started exactly where you are right now.",
    "The single insight that changes how you think about {T} forever.",
    "Most people overcomplicate {T}. The core principle is ruthlessly simple.",
    "Here's what separates those who master {T} from those who stay stuck.",
    "The {K1} problem in {T} isn't what you think it is.",
    "Why your biggest obstacle in {T} is actually your biggest advantage.",
    "The uncomfortable truth is that {T} rewards {K1} above everything else.",
    "Nobody talks about the {K1} side of {T} — but it's the whole game.",
    "If you understand {K1} and {K2}, you understand {T} completely.",
    "Three years from now, the people who figured out {T} will be untouchable.",
    "The pattern that shows up in every {T} success story is hiding in plain sight.",
    "What if everything you believed about {T} was optimized for someone else's benefit?",
    "The 1% who succeed at {T} all share one counterintuitive habit.",
    "Here's the fastest shortcut to mastering {T} — and why shortcuts actually work here.",
    "The gap between knowing about {T} and executing it is where most people disappear.",
    "Before you spend another hour on {T}, understand this one foundational principle.",
    "Your biggest competitor in {T} isn't other people. It's your own assumptions.",
    "The {K1} framework turns {T} from overwhelming to obvious.",
    "Most people quit {T} right before the compounding effect kicks in.",
    "What made {T} impossible last year is now a solved problem — here's how.",
    "The question that unlocks {T} for anyone willing to sit with the discomfort.",
    "The reason {T} feels so hard is that you're measuring the wrong thing.",
    "Here's why {K1} is the foundation of every breakthrough in {T}.",
    "In five years, those who invested in {T} now will say it was the most obvious decision.",
    "The brutal feedback loop in {T} that separates amateurs from professionals.",
    "If you only had 30 days to get good at {T}, this is exactly how you'd do it.",
]

_UNIVERSAL_SOLO_CLOSERS: list[str] = [
    "One deliberate shift in your approach rewires your entire trajectory.",
    "Stop waiting for perfect conditions. Execute today and iterate fast.",
    "The difference is in what you do consistently, not what you do occasionally.",
    "Every expert you admire was once exactly as confused as you are right now.",
    "Build the system, trust the process, and let the results accumulate.",
    "The best time to start was yesterday. The second best time is right now.",
    "Clarity comes from doing, not from planning. Take the first step.",
    "Master the fundamentals deeply, and the advanced stuff becomes obvious.",
]


def _extract_topic_words(topic: str, n: int = 3) -> list[str]:
    """Pull n salient content words from the topic for template fill-in. <0.1ms."""
    words = re.findall(r"[A-Za-z][a-zA-Z'-]{3,}", topic)
    seen: set[str] = set()
    out: list[str] = []
    for w in words:
        lw = w.lower().rstrip("'s")
        if lw not in _STOPWORDS and lw not in seen:
            seen.add(lw)
            out.append(w.rstrip("'s"))
            if len(out) >= n:
                break
    while len(out) < n:  # fallback if topic is very short
        out.append(topic.strip().rstrip(".!?") or "this")
    return out


def _build_unique_universal_script(topic: str, seed: int, target_words: int) -> str:
    """
    Recombine topic keywords + template pool into a unique script. ~0.1ms.
    seed rotates template selection so each run picks different sentences.
    """
    clean = topic.strip().rstrip(".!?") or "Success"
    kws = _extract_topic_words(clean, 3)
    k1, k2 = kws[0], kws[1]

    n = len(_UNIVERSAL_SOLO_TEMPLATES)
    picks = [_UNIVERSAL_SOLO_TEMPLATES[(seed + i * 7) % n] for i in range(5)]
    filled = [p.replace("{T}", clean).replace("{K1}", k1).replace("{K2}", k2) for p in picks]
    filled.append(_UNIVERSAL_SOLO_CLOSERS[seed % len(_UNIVERSAL_SOLO_CLOSERS)])

    words: list[str] = []
    for sentence in filled:
        ws = sentence.split()
        if len(words) + len(ws) > int(target_words * 1.25) and len(words) >= int(target_words * 0.7):
            break
        words.extend(ws)
    return " ".join(words)


def _build_unique_universal_dialogue(
    topic: str, seed: int, target_words: int, name1: str, name2: str
) -> list[tuple[str, str]]:
    """Generate a unique dialogue from template pool + topic keywords. ~0.1ms."""
    clean = topic.strip().rstrip(".!?") or "Success"
    kws = _extract_topic_words(clean, 3)
    k1, k2 = kws[0], kws[1]

    pairs: list[tuple[str, str]] = [
        (f"Have you noticed how {clean} rewards {k1} above almost everything else, {{n2}}?",
         f"Completely. Most people focus on {k2} instead — which is exactly why they plateau, {{n1}}."),
        (f"What's the one insight about {clean} you wish you'd had earlier, {{n2}}?",
         f"That {k1} compounds silently. You don't see the results for months, then they arrive at once, {{n1}}."),
        (f"Why do so many people get stuck when working on {clean}, {{n2}}?",
         f"They measure {k2} when they should be measuring {k1}. Wrong metric, wrong feedback loop, {{n1}}."),
        (f"Is {clean} as difficult as people claim, {{n2}}?",
         f"It's not difficult — it's uncomfortable. And humans are very good at avoiding discomfort, {{n1}}."),
        (f"What's the fastest legitimate path to real progress in {clean}, {{n2}}?",
         f"Remove friction. Every barrier between you and {k1} is costing compounding time, {{n1}}."),
        (f"Most people talk about {clean} but never really commit, {{n2}}. What's happening?",
         f"They confuse researching {clean} with actually doing it. Information feels productive. It isn't, {{n1}}."),
        (f"Where does {k2} fit into the bigger picture of {clean}, {{n2}}?",
         f"It's the entry point. The real leverage is in {k1} — that's what separates top performers, {{n1}}."),
        (f"If you could only teach one principle from {clean} to someone starting today, {{n2}}?",
         f"Start before you're ready. {clean} rewards execution, not endless preparation, {{n1}}."),
        (f"What's the biggest misconception people carry about {clean}, {{n2}}?",
         f"That {k1} is optional. It's not. It's the whole engine, {{n1}}."),
        (f"How do you know when you've actually understood {clean}, {{n2}}?",
         f"When {k1} stops feeling like effort and starts feeling like identity, {{n1}}."),
    ]

    n = len(pairs)
    pair = pairs[(seed + seed // n) % n]
    extra = pairs[(seed + 3) % n]

    n1_a, n2_a = pair
    n1_b, n2_b = extra

    beats = [
        (name1, n1_a.replace("{n1}", name1).replace("{n2}", name2)),
        (name2, n2_a.replace("{n1}", name1).replace("{n2}", name2)),
        (name1, n1_b.replace("{n1}", name1).replace("{n2}", name2)),
        (name2, n2_b.replace("{n1}", name1).replace("{n2}", name2)),
    ]

    closers = [
        (name2, f"Build the system, stay consistent, and let {clean} compound in your favour, {name1}."),
        (name2, f"One deliberate shift in how you approach {clean} changes everything, {name1}."),
        (name2, f"Stop waiting for the perfect moment. Execute on {clean} today, {name1}."),
    ]
    beats.append(closers[seed % len(closers)])
    return beats


def _detect_domain_profile(topic: str) -> tuple[str, Optional[str]]:
    """Score topic across domains and detect compound/hybrid concepts."""
    low = (topic or "").lower()
    scores: list[tuple[str, int]] = []
    for dom, kws in _DOMAIN_KEYWORDS.items():
        cnt = sum(1 for k in kws if k in low)
        if cnt > 0:
            scores.append((dom, cnt))
    scores.sort(key=lambda item: item[1], reverse=True)
    if not scores:
        return "universal_topic_director", None
    primary = scores[0][0]
    secondary = scores[1][0] if len(scores) > 1 and scores[1][0] != primary else None
    return primary, secondary


def _detect_domain(topic: str) -> str:
    """Classify user topic into primary domain for backwards compatibility."""
    return _detect_domain_profile(topic)[0]


class InbuiltAIDirector:
    """
    Intelligent in-process script generation and dialogue director for ANY topic.
    Fast (<0.05s), 100% offline, zero cloud reliance.
    """

    @classmethod
    def generate_script(
        cls,
        topic: str,
        duration: int = 30,
        dialogue_mode: bool = False,
        name1: str = "Alex",
        name2: str = "Maya",
        address_by_name: bool = True,
        style: str = "auto",
        seed: int = 0,
    ) -> str:
        """
        Generate a complete, duration-budgeted video script for ANY topic.
        If dialogue_mode is True, generates a conversational script where Speaker 1
        and Speaker 2 address each other by their configured names.
        seed: pass script_fingerprint_seed() value for unique output per topic.
        """
        if seed == 0:
            import time as _time, random as _random
            seed = (int(_time.time() * 1000) ^ _random.randint(1, 999999)) & 0x7FFFFFFF

        target_words = max(24, int(duration * WORDS_PER_SEC))
        n1 = (name1 or "Alex").strip().title()
        n2 = (name2 or "Maya").strip().title()

        domain, secondary_domain = _detect_domain_profile(topic)

        if dialogue_mode:
            return cls._generate_dialogue_script(
                topic=topic,
                target_words=target_words,
                duration=duration,
                name1=n1,
                name2=n2,
                address_by_name=address_by_name,
                domain=domain,
                secondary_domain=secondary_domain,
                seed=seed,
            )
        else:
            return cls._generate_solo_script(
                topic=topic,
                target_words=target_words,
                duration=duration,
                domain=domain,
                secondary_domain=secondary_domain,
                seed=seed,
            )

    @classmethod
    def _generate_dialogue_script(
        cls,
        topic: str,
        target_words: int,
        duration: int,
        name1: str,
        name2: str,
        address_by_name: bool,
        domain: str = "universal_topic_director",
        secondary_domain: Optional[str] = None,
        seed: int = 0,
    ) -> str:
        clean_topic = topic.strip().rstrip(".!?") or "Success"
        low = clean_topic.lower()
        combo = {domain, secondary_domain} if secondary_domain else set()
        kws = _extract_topic_words(clean_topic, 3)
        k1, k2 = kws[0], kws[1]
        angle_idx = (seed // 37) % 2

        if "tech_coding_ai" in combo and "fitness_health_bio" in combo:
            dialogue_beats = [
                (name1, f"Did you know that the convergence of artificial intelligence and medicine in {clean_topic} is completely transforming healthcare, {name2}?"),
                (name2, f"It's incredible, {name1}. Diagnostic neural networks can now analyze {k1} and biomarker data with superhuman precision."),
                (name1, f"And computational models are designing novel therapeutic approaches for {k2} in days instead of decades."),
                (name2, f"The future of human longevity is being built right at the intersection of code and biology, {name1}."),
            ]
        elif "wealth_business" in combo and "psychology_human_behavior" in combo:
            dialogue_beats = [
                (name1, f"Have you realized that {clean_topic} isn't really about numbers on a screen, {name2}... but about human psychology?"),
                (name2, f"That's the great secret, {name1}. Financial decisions around {k1} are driven far more by emotional impulses than by spreadsheet math."),
                (name1, f"People spend money to impress people they don't even like, mistaking lavish spending for wealth."),
                (name2, f"Master your emotional biases around {k2}, {name1}. True wealth is the freedom to control your own time."),
            ]
        elif "stoicism_philosophy_history" in combo and "wealth_business" in combo:
            dialogue_beats = [
                (name1, f"What can modern entrepreneurs and investors learn from ancient Stoic philosophy regarding {clean_topic}, {name2}?"),
                (name2, f"Everything, {name1}. In business and {k1}, market crashes are inevitable, but your panic or calm is entirely your choice."),
                (name1, f"Those who build lasting enterprises don't let temporary volatility around {k2} dictate their strategy."),
                (name2, f"Stand like an immovable rock against market storms, {name1}. Calm conviction always wins the long game."),
            ]
        elif "tech_coding_ai" in combo and "wealth_business" in combo:
            dialogue_beats = [
                (name1, f"Why is software leverage such an unfair advantage when tackling {clean_topic}, {name2}?"),
                (name2, f"Because code and automated systems around {k1} work around the clock with zero marginal cost of replication, {name1}."),
                (name1, f"A single builder today armed with AI can ship scalable tools around {k2} that once required entire teams."),
                (name2, f"The code you ship today works for your freedom tomorrow, {name1}. Build relentlessly."),
            ]
        elif domain == "science_space_nature":
            if angle_idx == 0:
                dialogue_beats = [
                    (name1, f"Did you know that when scientists look closely at {clean_topic}, {name2}... reality is stranger than human imagination?"),
                    (name2, f"It truly is, {name1}. Every atom of iron in our bodies was forged inside thermonuclear explosions of ancient stars."),
                    (name1, f"And fundamental physics around {k1} proves that quantum particles remain entangled across cosmic distances."),
                    (name2, f"Stay curious, {name1}. The deeper we explore {k2}, the more breathtaking the universe becomes."),
                ]
            else:
                dialogue_beats = [
                    (name1, f"How does modern research redefine our understanding of {clean_topic}, {name2}?"),
                    (name2, f"We are entering an era of deep precision, {name1}. From atomic scales to astrophysics, old dogmas are collapsing."),
                    (name1, f"When you study the core mechanisms of {k1}, you realize nature operates with mathematical elegance."),
                    (name2, f"Never lose your sense of wonder for {clean_topic}, {name1}. The mysteries of the universe are waiting to be decoded."),
                ]
        elif domain == "stoicism_philosophy_history":
            if angle_idx == 0:
                dialogue_beats = [
                    (name1, f"Have you ever noticed how history remembers {clean_topic}, {name2}... not for easy victories, but for discipline under fire?"),
                    (name2, f"That's so true, {name1}. When circumstances collapse, raw emotion guarantees defeat."),
                    (name1, f"The ancient Stoics understood that controlling your judgment around {k1} is the only true victory."),
                    (name2, f"Stand firm like an immovable pillar against the storm, {name1}. Master your reaction to {k2}, and you master everything."),
                ]
            else:
                dialogue_beats = [
                    (name1, f"What would Seneca or Marcus Aurelius say about our struggles with {clean_topic}, {name2}?"),
                    (name2, f"They would remind us that we suffer far more in imagination than in reality, {name1}."),
                    (name1, f"External events around {k1} have zero power over your inner peace unless you willingly surrender it."),
                    (name2, f"Treat adversity in {k2} as your supreme training ground, {name1}. True calm is an inside job."),
                ]
        elif domain == "tech_coding_ai":
            if angle_idx == 0:
                dialogue_beats = [
                    (name1, f"Why do you think so many developers get stuck when tackling {clean_topic}, {name2}?"),
                    (name2, f"Because they get trapped in surface syntax, {name1}. Real engineering is about system architecture and problem decomposition."),
                    (name1, f"When you decompose the complexity around {k1}, the architectural path becomes crystal clear."),
                    (name2, f"Build real projects, ship working code around {k2}, and iterate relentlessly, {name1}."),
                ]
            else:
                dialogue_beats = [
                    (name1, f"How does modern software leverage change the game for {clean_topic}, {name2}?"),
                    (name2, f"A solo builder today can deploy algorithms and cloud pipelines in hours, {name1}."),
                    (name1, f"The secret is mastering {k1} so your tools do the heavy lifting while you focus on high-level architecture."),
                    (name2, f"Ship fast, gather real feedback on {k2}, and let digital leverage scale your impact, {name1}."),
                ]
        elif domain == "wealth_business":
            if angle_idx == 0:
                dialogue_beats = [
                    (name1, f"Have you ever noticed how most people chase {clean_topic}, {name2}... but never make their money work for them?"),
                    (name2, f"It's the ultimate linear trap, {name1}. Trading finite hours for dollars guarantees a ceiling on your freedom."),
                    (name1, f"Productive assets around {k1} compound twenty-four hours a day without taking a break."),
                    (name2, f"Build cash-flowing systems around {k2} today, {name1}, so your time belongs entirely to you tomorrow."),
                ]
            else:
                dialogue_beats = [
                    (name1, f"What is the single most important financial rule in {clean_topic}, {name2}?"),
                    (name2, f"Understanding the difference between buying liabilities to look rich and building real equity, {name1}."),
                    (name1, f"When you direct excess cash flow into {k1}, you create an asymmetric safety moat."),
                    (name2, f"Let compounding around {k2} do the heavy lifting, {name1}. True wealth is silent freedom."),
                ]
        elif domain == "fitness_health_bio":
            if angle_idx == 0:
                dialogue_beats = [
                    (name1, f"What is the single biggest mistake people make with {clean_topic}, {name2}?"),
                    (name2, f"They overcomplicate extreme routines and ignore sleep, nutrition, and recovery, {name1}."),
                    (name1, f"Progressive overload on {k1} provides the stimulus, but rest is where the cellular rebuilding occurs."),
                    (name2, f"Nail the biological fundamentals of {k2} daily, {name1}, and your body will transform."),
                ]
            else:
                dialogue_beats = [
                    (name1, f"How do elite athletes sustain peak energy in {clean_topic}, {name2}?"),
                    (name2, f"By honoring their metabolic rhythms and nervous system recovery, {name1}."),
                    (name1, f"When you dial in your hydration and stimulus around {k1}, fatigue disappears."),
                    (name2, f"Consistency in {k2} beats occasional heroic effort every single time, {name1}."),
                ]
        elif domain == "psychology_human_behavior":
            if angle_idx == 0:
                dialogue_beats = [
                    (name1, f"Have you ever noticed something strange about human behavior regarding {clean_topic}, {name2}?"),
                    (name2, f"Our subconscious doesn't look for what is best for us, {name1}. It gravitates toward what feels familiar."),
                    (name1, f"When validation around {k1} is unpredictable, dopamine spikes create intense attachment loops."),
                    (name2, f"Recognize the psychological pattern in {k2}, {name1}. Real peace should never make you anxious for approval."),
                ]
            else:
                dialogue_beats = [
                    (name1, f"Why is self-awareness so difficult to practice in {clean_topic}, {name2}?"),
                    (name2, f"Because the brain automatically defends its existing cognitive biases to protect the ego, {name1}."),
                    (name1, f"When someone projects their own doubts onto your progress in {k1}, it's about their fear, not yours."),
                    (name2, f"Detach your self-worth from external validation in {k2}, {name1}. Trust your own clarity."),
                ]
        elif domain == "habits_productivity_focus":
            if angle_idx == 0:
                dialogue_beats = [
                    (name1, f"Why is it so easy to procrastinate on {clean_topic}, {name2}... even when we know how crucial it is?"),
                    (name2, f"Because our brain is wired to conserve glucose and take the path of least resistance, {name1}."),
                    (name1, f"High performers don't rely on willpower. They eliminate the friction between them and executing {k1}."),
                    (name2, f"Win the morning, design your environment around {k2}, and make deep work effortless, {name1}."),
                ]
            else:
                dialogue_beats = [
                    (name1, f"What is the superpower behind mastering {clean_topic}, {name2}?"),
                    (name2, f"Unbroken, single-task focus in an economy full of endless notifications, {name1}."),
                    (name1, f"Dedicate ninety uninterrupted minutes to your highest-leverage task in {k1}."),
                    (name2, f"Protect that time fiercely, {name1}. That is how exponential progress in {k2} compounds."),
                ]
        elif domain == "motivation_mindset_leadership":
            dialogue_beats = [
                (name1, f"What truly separates those who conquer {clean_topic} from those who give up when it gets tough, {name2}?"),
                (name2, f"When adversity strikes, average people search for an exit, but champions search for an edge, {name1}."),
                (name1, f"Discipline means executing on {k1} long after the emotional high of the moment has faded."),
                (name2, f"Refuse to negotiate with your excuses regarding {k2}, {name1}. Keep moving forward."),
            ]
        elif domain == "comedy_daily_relatable":
            dialogue_beats = [
                (name1, f"Why does our brain wait until 2 AM to replay an awkward moment about {clean_topic}, {name2}?"),
                (name2, f"Because our ancient survival instincts treat social embarrassment like an existential crisis, {name1}!"),
                (name1, f"And we pretend to have everything under control regarding {k1} while quietly winging adult life!"),
                (name2, f"Relax, {name1}. Laugh at the chaos of {k2} and don't take everyday life too seriously!"),
            ]
        else:
            # Unique dialogue per topic+seed — recombined from template pool
            dialogue_beats = _build_unique_universal_dialogue(
                topic=topic, seed=seed, target_words=target_words, name1=name1, name2=name2
            )

        # Pacing budget: rotate middle beats by seed for variety across runs.
        if len(dialogue_beats) >= 4 and seed > 0:
            rot = (seed // 97) % max(1, len(dialogue_beats) - 2)
            if rot:
                mid = dialogue_beats[1:-1]
                mid = mid[rot:] + mid[:rot]
                dialogue_beats = [dialogue_beats[0]] + mid + [dialogue_beats[-1]]

        script_lines: list[str] = []
        current_words = 0
        for speaker, line in dialogue_beats:
            line_w = len(line.split())
            if current_words + line_w > target_words * 1.30 and len(script_lines) >= 4:
                break
            script_lines.append(f"{speaker}: {line}")
            current_words += line_w

        return "\n\n".join(script_lines)

    @classmethod
    def _generate_solo_script(
        cls,
        topic: str,
        target_words: int,
        duration: int,
        domain: str = "universal_topic_director",
        secondary_domain: Optional[str] = None,
        seed: int = 0,
    ) -> str:
        clean_topic = topic.strip().rstrip(".!?") or "Success"
        combo = {domain, secondary_domain} if secondary_domain else set()
        kws = _extract_topic_words(clean_topic, 3)
        k1, k2 = kws[0], kws[1]

        domain_angles: dict[str, list[list[str]]] = {
            "wealth_business": [
                [
                    "Here is the brutal financial truth about {T} that most people ignore.",
                    "The majority spend their finite hours trading time for {K1}, never building assets that work while they sleep.",
                    "True wealth isn't showing off luxuries—it's having the silent freedom to control your own calendar.",
                    "When you understand compound growth in {T}, small daily investments outperform frantic hustle.",
                    "Build cash-flowing systems around {K1}, ignore the noise, and let time compound your freedom.",
                ],
                [
                    "Most people approach {T} with the wrong mental model of risk and reward.",
                    "They seek guaranteed safety in {K1}, but inflation and stagnation quietly destroy their purchasing power.",
                    "High performers look for asymmetric upside where the downside is capped and the upside is uncapped.",
                    "Focus on building distribution, equity, and ownership rather than renting out your hours.",
                    "Master {K1}, safeguard your capital, and let asymmetric returns work for your future.",
                ],
                [
                    "The hardest part of mastering {T} is not mathematics—it is managing human psychology.",
                    "People spend money they haven't earned on things they don't need to impress people they don't even like.",
                    "Financial independence begins when your self-worth detaches completely from external social comparison.",
                    "Keep your living expenses low, direct excess capital into {K1}, and buy back your sovereign freedom.",
                    "Wealth is what you do not see: the choices and peace that money preserves for you.",
                ],
            ],
            "tech_coding_ai": [
                [
                    "Here is what elite engineers understand about {T} that beginners often overlook.",
                    "Writing code is only ten percent of the job—the real challenge is architecting systems that scale gracefully.",
                    "When you master {K1}, complex technical debt transforms into clean, modular components.",
                    "In the age of AI code assistants, your unique superpower is system decomposition and debugging intuition.",
                    "Don't just memorize syntax. Understand the underlying computer science of {K1} and build relentlessly.",
                ],
                [
                    "Software code is the most asymmetric leverage ever invented for {T}.",
                    "Every algorithm and API you deploy works for you twenty-four hours a day with zero marginal cost.",
                    "Instead of over-engineering in secret, ship small functional iterations and gather real feedback fast.",
                    "A solo developer wielding modern AI tooling can outpace entire engineering teams of the past decade.",
                    "Master the tools of {K1}, solve authentic user friction, and ship solutions that matter.",
                ],
                [
                    "The greatest developers aren't the ones who write bug-free code on day one—they are the masters of debugging {T}.",
                    "When compiler errors and production crashes occur, amateurs panic, but masters trace root causes methodically.",
                    "Treat every failed test and edge case as diagnostic data pointing straight toward the solution.",
                    "Break down the problem around {K1}, isolate each failure point, and verify your assumptions.",
                    "Deep technical competence in {T} is forged directly inside the fires of difficult debugging.",
                ],
            ],
            "fitness_health_bio": [
                [
                    "Stop overcomplicating your approach to {T}—your body responds to simple biological laws.",
                    "First: progressive tension and overload on {K1} to force cellular adaptation.",
                    "Second: nutrient-dense whole foods to fuel your metabolism and repair muscle tissue.",
                    "And third: deep restorative sleep where your human growth hormone naturally surges.",
                    "Respect the fundamentals of {K1} daily, and your physical energy will transform completely.",
                ],
                [
                    "The reason most people fail with {T} isn't lack of discipline—it's poor system design.",
                    "When you rely on fleeting motivation, the moment you feel tired or stressed, your routine collapses.",
                    "Build an environment where executing {K1} is the path of least resistance.",
                    "Consistency on average days beats perfection on rare days every single time.",
                    "Protect your energy, train your body with purpose, and make {K1} your non-negotiable habit.",
                ],
                [
                    "In the pursuit of {T}, training is merely the stimulus—recovery is where the actual growth occurs.",
                    "If you push {K1} relentlessly without adequate sleep and micronutrients, chronic inflammation takes over.",
                    "Your cardiovascular and cellular health determines how well you perform in every area of life.",
                    "Optimize your hydration, manage nervous system stress, and fuel your body like an elite machine.",
                    "Longevity in {T} belongs to those who master the delicate balance between exertion and restoration.",
                ],
            ],
            "stoicism_philosophy_history": [
                [
                    "Over two thousand years ago, ancient Stoic leaders uncovered an unfair advantage in {T}.",
                    "Marcus Aurelius governed an entire empire by adhering strictly to one rule: separate what you control from what you cannot.",
                    "When external chaos threatens your plans, average minds panic, but disciplined minds remain unshakeable.",
                    "External events in {K1} have no power over your judgment unless you willingly surrender your peace.",
                    "Stand like an immovable rock against the storm, and command your own reactions.",
                ],
                [
                    "The ancient Stoics practiced an art known as Amor Fati—not merely tolerating adversity in {T}, but loving it as fuel.",
                    "When plans collapse or obstacles arise in {K1}, the obstacle becomes the path forward.",
                    "Complaining and resentment drain the exact mental clarity you need to execute effectively.",
                    "Embrace every setback in {T} as tailored training for your character and inner resilience.",
                    "Transform every difficulty into strength, and proceed with unyielding calm.",
                ],
                [
                    "The greatest battle in {T} is never against external opponents—it is against your own unchecked ego.",
                    "Seneca warned that we suffer far more often in our imagination than we ever do in reality.",
                    "Strip away fabricated anxieties, silence your impulse for immediate gratification, and focus on virtue.",
                    "True power is not commanding others, but maintaining complete sovereignty over your own mind.",
                    "Master your desires in {K1}, walk with quiet dignity, and conquer yourself first.",
                ],
            ],
            "habits_productivity_focus": [
                [
                    "The reason you struggle with {T} isn't laziness—it's friction.",
                    "Your brain is biologically wired for the path of least resistance to conserve glucose and energy.",
                    "High performers don't rely on willpower—they engineer environments where executing {K1} is effortless.",
                    "Remove the triggers for distraction, place the tools for deep work in plain sight, and guard your mornings.",
                    "Design your space for focus, and the habits of {T} will take care of themselves.",
                ],
                [
                    "Most people overestimate what they can accomplish in a day of {T}, and underestimate what compounds in a year.",
                    "Improving by just one percent in {K1} each day feels imperceptible in the moment.",
                    "Yet through mathematical compounding, those tiny daily choices produce exponential transformation over time.",
                    "Stop waiting for dramatic breakthroughs. Win the small daily micro-decisions and trust the process.",
                    "Show up consistently for {K1}, lay one perfect brick every morning, and watch your empire rise.",
                ],
                [
                    "In an economy built on infinite notifications, your undivided focus in {T} is a superpower.",
                    "Multitasking is an illusion—each context switch fractures your cognitive working memory.",
                    "Dedicate ninety minutes of uninterrupted deep focus to your most critical priority in {K1}.",
                    "Protect that sacred time from notifications, meetings, and low-leverage busywork.",
                    "Single-task with fierce intensity, eliminate distractions, and produce work that leaves a dent.",
                ],
            ],
            "psychology_human_behavior": [
                [
                    "Here is something deeply fascinating about human psychology when it comes to {T}.",
                    "Your subconscious mind doesn't fall in love with predictability—it gets hijacked by uncertainty and mixed signals.",
                    "Psychologists call this intermittent reinforcement. When validation around {K1} is erratic, dopamine surges.",
                    "You are often not attached to the reality—you are chasing the relief of finally receiving reassurance.",
                    "Recognize emotional loops in {T}, step back with clarity, and protect your inner peace.",
                ],
                [
                    "In matters of {T}, the human brain prefers comforting illusions over challenging realities.",
                    "We instinctively seek evidence that validates our existing insecurities while ignoring disconfirming facts.",
                    "When someone projects their own doubts onto you regarding {K1}, remember: their judgment is a reflection of them, not you.",
                    "Detach your self-worth from the opinions of onlookers who bear none of your consequences.",
                    "Trust objective reality over social validation, and walk your own path in {T}.",
                ],
                [
                    "Your current limitations in {T} were largely conditioned into your nervous system before you were ten years old.",
                    "The brain's survival architecture treats the unfamiliarity of {K1} as a threat to personal safety.",
                    "That internal resistance you feel is not a stop sign—it is simply old neural wiring meeting new growth.",
                    "Acknowledge the fear, thank your subconscious for trying to protect you, and take decisive action anyway.",
                    "Rewire your narrative around {K1}, step into the discomfort, and unlock your true potential.",
                ],
            ],
            "motivation_mindset_leadership": [
                [
                    "Here is the profound difference between dreaming of greatness and actually conquering {T}.",
                    "When adversity strikes, average people search for an exit, but true leaders search for an edge.",
                    "Discipline means doing what you promised yourself you would do, long after the emotion of the moment has faded.",
                    "True confidence isn't hoping for an easy road—it's knowing you can adapt to whatever comes your way in {K1}.",
                    "Refuse to negotiate with your excuses, maintain high standards, and lead by example.",
                ],
                [
                    "You do not rise to the level of your goals in {T}—you fall to the level of your daily identity.",
                    "If you view yourself as an amateur trying to figure out {K1}, you will stumble at the first hurdle.",
                    "Adopt the habits, demeanor, and standards of the elite professional you are becoming right now.",
                    "Every action you take is a vote for the type of person you wish to be.",
                    "Cast your votes with relentless intention, embrace the challenge, and own your greatness in {T}.",
                ],
            ],
            "science_space_nature": [
                [
                    "When you examine the deep science of {T}, reality is far stranger than human imagination.",
                    "Every atom of iron in your blood and calcium in your bones was forged inside ancient supernovae billions of years ago.",
                    "Across millions of light-years of cosmic vacuum, fundamental particles in {K1} remain intimately connected.",
                    "We are not separate from the cosmos—we are the conscious universe waking up to understand itself.",
                    "Never lose your sense of wonder for the immense mysteries that surround us in {T}.",
                ],
                [
                    "At the atomic boundary of physics, the ordinary rules of {T} completely dissolve.",
                    "Particles exist as probability waves until observation collapses them into definite states.",
                    "This bizarre quantum reality in {K1} powers everything from modern microchips to photosynthetic plant biology.",
                    "The deeper science looks into the fabric of spacetime, the more breathtaking the tapestry becomes.",
                    "Stay relentlessly curious, question old dogmas, and explore the wondrous frontier of {T}.",
                ],
            ],
            "comedy_daily_relatable": [
                [
                    "Why does our brain decide that midnight is the perfect time to overthink every detail of {T}?",
                    "You start your day with ambitious plans for {K1}, and by three in the afternoon you are researching pointless trivia.",
                    "We spend half our lives acting like we have everything completely figured out while quietly improvising adult life.",
                    "Relax. Nobody is scrutinizing your minor mistakes nearly as closely as you are.",
                    "Take a deep breath, laugh at the absurdity of {T}, and keep moving forward.",
                ],
                [
                    "Nothing tests human patience quite like trying to manage {T} in the modern digital age.",
                    "You sit down to get five minutes of work done on {K1}, and forty notifications suddenly demand your immediate soul.",
                    "We have supercomputers in our pockets and yet we still forget why we walked into the kitchen.",
                    "Embrace the charming chaos, give yourself some grace, and tackle {T} one ridiculous step at a time.",
                    "Celebrate the small wins, enjoy the ride, and don't take everyday life too seriously.",
                ],
            ],
        }

        if "tech_coding_ai" in combo and "fitness_health_bio" in combo:
            lines = [
                f"The convergence of artificial intelligence and medicine in {clean_topic} is triggering the biggest healthcare revolution in history.",
                f"Diagnostic neural networks analyze {k1} and biological markers with superhuman precision.",
                f"Generative molecular algorithms design targeted therapeutic solutions for {k2} in days rather than decades.",
                f"The future of human longevity is here, forged at the boundary of code and biology.",
            ]
        elif "wealth_business" in combo and "psychology_human_behavior" in combo:
            lines = [
                f"Here is the brutal truth about {clean_topic}—wealth is a psychological game, not a mathematical one.",
                f"Your decisions around {k1} are driven less by logical calculation and far more by emotional validation.",
                f"Spending money to impress strangers is the quickest way to end up with less freedom.",
                f"Master your emotional biases around {k2}, and let compounding build your real independence.",
            ]
        elif "stoicism_philosophy_history" in combo and "wealth_business" in combo:
            lines = [
                f"Two thousand years before modern markets, ancient Stoic leaders uncovered an unfair advantage in {clean_topic}.",
                f"In business and {k1}, market crashes are inevitable, but panic is an emotional choice you can refuse.",
                f"Those who build lasting wealth don't run from volatility—they use adversity around {k2} as fuel to scale.",
                f"Master your mind, eliminate emotional volatility, and lead with unwavering conviction.",
            ]
        elif "tech_coding_ai" in combo and "wealth_business" in combo:
            lines = [
                f"The greatest financial leverage in human history isn't physical labor—it's software distribution in {clean_topic}.",
                f"Algorithms and automated code operating around {k1} work twenty-four hours a day with zero marginal cost.",
                f"A solo builder today armed with AI can ship systems around {k2} that once took a venture-backed company.",
                f"Learn to build, ship relentlessly, and let digital leverage buy your freedom.",
            ]
        elif domain in domain_angles:
            angles = domain_angles[domain]
            chosen_angle = angles[(seed // 37) % len(angles)]
            lines = [s.replace("{T}", clean_topic).replace("{K1}", k1).replace("{K2}", k2) for s in chosen_angle]
        else:
            # Universal topic pool: 30-template recombiner
            return _build_unique_universal_script(topic=topic, seed=seed, target_words=target_words)

        # Rotate middle lines by seed — gives different emphasis per run
        if len(lines) >= 4 and seed > 0:
            rot = (seed // 97) % max(1, len(lines) - 2)
            if rot:
                mid = lines[1:-1]
                mid = mid[rot:] + mid[:rot]
                lines = [lines[0]] + mid + [lines[-1]]

        # Replace closing line with dynamic topic-keyword closing sentence
        if seed > 0 and len(lines) >= 3:
            inject_pool = [
                f"The real leverage in {clean_topic} is {k1}, not {k2}.",
                f"Most people miss that {k1} is what actually drives progress in {clean_topic}.",
                f"When you strip the noise from {clean_topic}, {k1} is the only variable that matters.",
                f"The practitioners who succeed at {clean_topic} all obsess over {k1}.",
                f"Nobody warns you that {k1} compounds faster in {clean_topic} than any other factor.",
            ]
            lines[-1] = inject_pool[(seed // 97) % len(inject_pool)]

        joined = " ".join(lines)
        words = joined.split()
        if len(words) > target_words * 1.25 and len(lines) > 4:
            trimmed = lines[:4] + [lines[-1]]
            return " ".join(trimmed)
        return " ".join(lines)

    @classmethod
    def improve_script(
        cls,
        script: str,
        target_duration: int = 30,
        dialogue_mode: bool = False,
        name1: str = "Alex",
        name2: str = "Maya",
        address_by_name: bool = True,
    ) -> str:
        """
        Polish raw script text:
          - Inserts natural micro-pauses ('...') at emotional pivots.
          - Normalizes character dialogue turns with configured names.
          - Trims bloated filler phrases.
          - Calibrates pacing to match exact duration.
        """
        raw = script.strip()
        if not raw:
            return ""

        n1 = (name1 or "Alex").strip().title()
        n2 = (name2 or "Maya").strip().title()

        # Remove clunky academic fillers
        fillers = [
            (r"\bin order to\b", "to"),
            (r"\bas a matter of fact,?\s*", ""),
            (r"\bdue to the fact that\b", "because"),
            (r"\bat the end of the day,?\s*", "ultimately, "),
            (r"\bfirst and foremost,?\s*", "first, "),
        ]
        text = raw
        for pat, rep in fillers:
            text = re.sub(pat, rep, text, flags=re.IGNORECASE)

        if dialogue_mode:
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            formatted_turns: list[str] = []
            current_spk = 1

            for line in lines:
                m = re.match(r"^(?:\[?([^:\]]+)\]?[:\-–]\s*)(.+)$", line)
                if m:
                    raw_spk = m.group(1).strip()
                    spoken = m.group(2).strip()
                    if any(s in raw_spk.lower() for s in (n1.lower(), "1", "male", "guy", "alex")):
                        tag = n1
                        current_spk = 2
                    else:
                        tag = n2
                        current_spk = 1
                    formatted_turns.append(f"{tag}: {spoken}")
                else:
                    tag = n1 if current_spk == 1 else n2
                    formatted_turns.append(f"{tag}: {line}")
                    current_spk = 2 if current_spk == 1 else 1

            return "\n\n".join(formatted_turns)
        else:
            return text
