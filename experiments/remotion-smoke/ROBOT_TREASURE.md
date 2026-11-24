# Robot Treasure

Run `npm install`, generate the soundtrack with `python scripts/make_robot_audio.py` (requires espeak, numpy and scipy), and run `npx remotion render src/robot.jsx RobotTreasure out/robot-treasure.mp4 --codec h264 --concurrency 2`.

12 seconds, 1080x1920, 30 fps. All geometry, typography, animation, music, and SFX are procedural; narration uses local eSpeak. The workflow checks the frame count, codecs, dimensions, duration and full decode. Native Remotion result is pending until CI passes.
