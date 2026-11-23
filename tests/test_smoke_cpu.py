"""CPU-only regression smoke tests for the public Stickman Studio pipeline.

These tests do not require model downloads, a GPU, or a GUI.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image, ImageDraw, ImageStat
from engine.inbuilt_ai_director import InbuiltAIDirector
from engine.cis_storyboard_planner import CISStoryboardPlanner
from engine.cis_scene_illustrator import CISSceneIllustrator
from engine.procedural_object_engine import ProceduralObjectEngine

TOPICS = [
    "Why do stars eventually die?",
    "A lonely robot discovers a signal from a lost civilization",
    "Why do algorithms need formal proofs?",
]

class CPUContentSmoke(unittest.TestCase):
    def test_three_topics_generate_storyboards_without_llm(self):
        planner = CISStoryboardPlanner(llm_manager=None)
        for i, topic in enumerate(TOPICS):
            with self.subTest(topic=topic):
                script = InbuiltAIDirector.generate_script(
                    topic=topic, duration=20, seed=101 + i
                )
                self.assertGreater(len(script.split()), 10, script)
                scenes = planner.plan(script=script, topic=topic, visual_style="B1")
                self.assertGreaterEqual(len(scenes), 1)
                for scene in scenes:
                    self.assertTrue(scene.get("narration"))
                    self.assertTrue(scene.get("choreography"))
                    self.assertTrue(scene.get("scene_id"))

    def test_first_scene_renders_without_uploaded_assets(self):
        topic = TOPICS[1]
        script = InbuiltAIDirector.generate_script(topic=topic, duration=20, seed=907)
        scenes = CISStoryboardPlanner(llm_manager=None).plan(
            script=script, topic=topic, visual_style="B1"
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "scene.png"
            result = CISSceneIllustrator(mode="pil", aspect_ratio="9:16").illustrate(
                scenes[0], str(output)
            )
            self.assertTrue(result)
            self.assertTrue(output.exists())
            with Image.open(output) as img:
                self.assertEqual(img.size, (1080, 1920))
                rgb = img.convert("RGB").resize((90, 160))
                self.assertGreater(max(ImageStat.Stat(rgb).stddev), 1)

    def test_unknown_prop_has_rendered_fallback(self):
        image = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        drawn = ProceduralObjectEngine.draw_object(
            ImageDraw.Draw(image), "unknown hypothetical quantum widget",
            10, 10, 180, 180, seed=123
        )
        self.assertTrue(drawn)
        self.assertIsNotNone(image.getbbox())

if __name__ == "__main__":
    unittest.main()
