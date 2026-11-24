import React,{useRef,useLayoutEffect} from 'react';
import {AbsoluteFill,Composition,registerRoot,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';
import {Audio} from '@remotion/media';
import {draw} from './robot-scene.js';
function Reel(){const frame=useCurrentFrame();const {fps,width,height}=useVideoConfig();const ref=useRef(null);useLayoutEffect(()=>{draw(ref.current.getContext('2d'),frame/fps,width,height)},[frame,fps,width,height]);return <AbsoluteFill><canvas ref={ref} width={width} height={height}/><Audio src={staticFile('soundtrack.wav')}/></AbsoluteFill>}
function Root(){return <Composition id="RobotTreasure" component={Reel} durationInFrames={360} fps={30} width={1080} height={1920}/>};registerRoot(Root);
