import React from 'react';
import {AbsoluteFill,Composition,Easing,interpolate,registerRoot,staticFile,useCurrentFrame} from 'remotion';
import {Audio} from '@remotion/media';

// Creative treatment: a single continuous, character-led tracking shot.
// This is NOT the geometry-matched smoke test. All imagery is original procedural SVG.
const cl={extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;
const lerp=(f:number,x:number[],y:number[])=>interpolate(f,x,y,cl);
const s=(x:number)=>Math.round(x*10)/10;
const buildings=Array.from({length:19},(_,i)=>({x:i*102-110,w:82+(i*19%35),h:185+(i*83%270),id:i}));
const motes=Array.from({length:55},(_,i)=>({x:(i*163+71)%1470,y:(i*103+33)%620,r:1+(i%3),speed:.25+(i%5)*.18}));
const Robot:React.FC<{f:number}> = ({f})=>{
 const walk=lerp(f,[0,15,100,123,360],[0,1,1,0,0]);
 const stride=Math.sin(f*.5)*walk;
 const bob=Math.abs(Math.sin(f*.5))*3.8*walk;
 const x=lerp(f,[0,15,115,135],[185,185,571,571]);
 const bend=lerp(f,[123,167,196,210],[0,0,18,10]);
 const arm=lerp(f,[128,184,234,266],[0,0,1,1]);
 const headTilt=lerp(f,[147,187,230],[0,11,5]);
 const wake=lerp(f,[247,296,345],[0,1,1]);
 return <g transform={`translate(${x} ${532+bob+bend})`}>
   <ellipse cx="0" cy="67" rx="49" ry="9" opacity=".55" fill="#010915"/>
   <g stroke="#D9E6F0" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round" fill="none">
     <path d={`M-18 -4 L${-24+23*stride} 29 L${-27+41*stride} 69`}/>
     <path d={`M18 -4 L${24-23*stride} 29 L${27-41*stride} 69`}/>
     <path d={`M-28 -69 L${-41+8*stride} -34 L${-37+8*stride} -9`}/>
     <path d={`M28 -69 L${46-15*arm-8*stride} ${-33+8*arm} L${42+47*arm-8*stride} ${-9-29*arm}`}/>
   </g>
   <rect x="-31" y="-93" width="62" height="95" rx="17" stroke="#cbdbe5" strokeWidth="6" fill="#19384b"/>
   <path d="M-17 -60 L17 -60" stroke="#2f5666" strokeWidth="4"/>
   <rect x="-12" y="-46" width="24" height="9" rx="4" fill={wake>.2?'#ffe3a3':'#6ff8ff'}/>
   <g transform={`translate(0 -95) rotate(${headTilt})`}>
    <rect x="-43" y="-75" width="86" height="70" rx="19" fill="#d5e9f5" stroke="#f2faff" strokeWidth="3"/>
    <rect x="-32" y="-61" width="64" height="38" rx="12" fill="#0a2b41"/>
    <circle cx="-15" cy="-41" r="5" fill="#61edff"/>
    <circle cx="15" cy="-41" r="5" fill="#61edff"/>
    <path d="M0 -75 V-86" stroke="#b2d1e4" strokeWidth="5"/>
    <circle cy="-90" r="5" fill="#79eaff"/>
   </g>
 </g>
};
const Intro:React.FC<{f:number}> = ({f})=>{
 const op=lerp(f,[0,16,90,112],[0,1,1,0]);
 return <div style={{position:'absolute',left:88,top:105,opacity:op}}>
  <div style={{fontSize:16,letterSpacing:6,color:'#8ce6ff',fontWeight:700}}>AN ORIGINAL SHORT FILM</div>
  <div style={{fontSize:63,lineHeight:1.03,fontWeight:900,letterSpacing:-2,marginTop:18}}>THE LAST<br/>SIGNAL</div>
  <div style={{fontSize:19,color:'#c8dbe5',marginTop:19,letterSpacing:1}}>The world went silent. One remained.</div>
 </div>
};
const Scene:React.FC=()=>{
 const f=useCurrentFrame();
 const camera=lerp(f,[0,122,230,359],[0,-94,-134,-200]);
 const glow=lerp(f,[106,143,210,246,310],[0,.5,.65,1,1]);
 const awakening=lerp(f,[231,293,355],[0,.8,1]);
 const sky=lerp(f,[225,310,359],[0,.9,1]);
 const introFade=lerp(f,[132,167],[0,1])*lerp(f,[226,244],[1,0]);
 const finaleFade=lerp(f,[264,294],[0,1]);
 const finishing=lerp(f,[348,359],[1,0]);
 const ripple=Math.max(0,f-239)*18;
 return <AbsoluteFill style={{background:'#020612',fontFamily:"'Arial',sans-serif",color:'#f0f9ff',overflow:'hidden'}}>
  <Audio src={staticFile('creative-score.wav')}/>
  <svg viewBox="0 0 1280 720" width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
   <defs>
     <linearGradient id="night" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#06091a"/><stop offset=".55" stopColor="#13334c"/><stop offset="1" stopColor="#324c5a"/></linearGradient>
     <linearGradient id="dawn" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#16264f"/><stop offset=".55" stopColor="#cd7b71"/><stop offset="1" stopColor="#ffc981"/></linearGradient>
     <linearGradient id="road" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#1c333e"/><stop offset="1" stopColor="#030811"/></linearGradient>
     <radialGradient id="flare"><stop stopColor="#f9ffff"/><stop offset=".12" stopColor="#b8ffff" stopOpacity=".95"/><stop offset=".46" stopColor="#3fa8f9" stopOpacity=".35"/><stop offset="1" stopColor="#2689df" stopOpacity="0"/></radialGradient>
     <radialGradient id="sun"><stop stopColor="#ffeabd" stopOpacity=".96"/><stop offset=".27" stopColor="#ffdaac" stopOpacity=".42"/><stop offset="1" stopColor="#eaae8b" stopOpacity="0"/></radialGradient>
     <linearGradient id="edge" x1="0" x2="1"><stop stopColor="#050917" stopOpacity=".9"/><stop offset=".27" stopColor="#050917" stopOpacity="0"/><stop offset=".8" stopColor="#050917" stopOpacity="0"/><stop offset="1" stopColor="#050917" stopOpacity=".65"/></linearGradient>
   </defs>
   <rect width="1280" height="720" fill="url(#night)"/>
   <rect width="1280" height="720" fill="url(#dawn)" opacity={sky*.75}/>
   <circle cx="1010" cy="358" r="350" fill="url(#sun)" opacity={sky}/>
   {Array.from({length:38},(_,i)=><circle key={'star'+i} cx={(i*149+41)%1280} cy={(i*71+22)%320} r={i%5===0?1.8:1} fill="#bce5ff" opacity={(1-sky)*.65}/>)}
   <g transform={`translate(${camera*.25} 0)`}>
    {buildings.map(({x,w,h,id})=><g key={id}>
      <rect x={x} y={563-h} width={w} height={h+40} fill={id%2?'#101e2f':'#14283a'}/>
      {Array.from({length:12},(_,j)=>{const yy=574-h+Math.floor(j/3)*43;const xx=x+13+(j%3)*25;
        const reach=lerp(f,[230+Math.abs(xx-740)*.11,266+Math.abs(xx-740)*.11],[0,1]);
        return <rect key={j} x={xx} y={yy} width="9" height="13" rx="1" fill={j%5===1?'#ffcc91':'#8ee8ff'} opacity={(j%7===0?.25:.03)+reach*(.75-(j%4)*.1)}/>
      })}
    </g>)}
   </g>
   <g transform={`translate(${camera*.51} 0)`}>
    {Array.from({length:9},(_,i)=>{const hh=104+(i*61%152);return <g key={i}>
      <rect x={i*185-155} y={572-hh} width={162} height={hh+35} fill="#162937"/>
      <path d={`M${i*185-155} ${572-hh} h162`} stroke="#406076" strokeWidth="2" opacity=".5"/>
    </g>})}
   </g>
   <rect x="0" y="576" width="1280" height="144" fill="url(#road)"/>
   <path d="M0 575 H1280" stroke="#537181" strokeWidth="3"/>
   <path d="M0 656 H1280" stroke="#74919a" strokeDasharray="130 60" strokeWidth="3" opacity=".27"/>
   <g transform={`translate(${camera} 0)`}>
     <path d="M702 581 l28 12 25 -8 30 21" stroke="#5e8891" fill="none" strokeWidth="4" opacity=".63"/>
     <ellipse cx="738" cy="587" rx={86+glow*85} ry={12+glow*12} fill="#64d8ff" opacity={glow*.17}/>
     <circle cx="741" cy="572" r={215+glow*90} opacity={glow} fill="url(#flare)"/>
     <circle cx="741" cy="572" r={8+glow*11} opacity={glow} fill="#e3ffff"/>
     <Robot f={f}/>
     {Array.from({length:4},(_,i)=><circle key={i} cx="741" cy="572" r={ripple-i*100} stroke="#66dffa" strokeWidth="3" fill="none" opacity={ripple-i*100>0&&ripple-i*100<1100?Math.max(0,.65-(ripple-i*100)/1100):0}/>)}
   </g>
   {motes.map((p,i)=><circle key={i} cx={(p.x+f*p.speed)%1280} cy={p.y+Math.sin(f*.021+i)*8} r={p.r} fill={i%3===0?'#a7edff':'#bfdbe6'} opacity={.08+.20*glow}/>)}
   <rect width="1280" height="720" fill="url(#edge)"/>
   <rect width="1280" height="25" fill="#02030a"/><rect y="695" width="1280" height="25" fill="#02030a"/>
  </svg>
  <Intro f={f}/>
  <div style={{position:'absolute',left:88,top:130,opacity:introFade*finishing}}>
    <div style={{fontSize:16,letterSpacing:5,fontWeight:700,color:'#75e4ff'}}>CHAPTER II / DISCOVERY</div>
    <div style={{fontSize:43,lineHeight:1.14,fontWeight:900,marginTop:14}}>BENEATH THE SILENCE,<br/>A HEARTBEAT.</div>
  </div>
  <div style={{position:'absolute',left:87,top:104,opacity:finaleFade*finishing}}>
    <div style={{fontSize:17,letterSpacing:5,color:'#a5ecff'}}>CHAPTER III / AWAKENING</div>
    <div style={{fontSize:58,fontWeight:900,marginTop:14,letterSpacing:-1}}>THE CITY<br/>REMEMBERS.</div>
  </div>
  <div style={{position:'absolute',bottom:51,left:90,letterSpacing:4,fontSize:13,color:'#d6effc',opacity:.9*finishing}}>A STORY OF ONE SMALL LIGHT</div>
  <div style={{position:'absolute',bottom:51,right:90,fontSize:13,letterSpacing:3,color:'#a3d5e6',opacity:.85*finishing}}>REMOTION · ORIGINAL MOTION DESIGN</div>
 </AbsoluteFill>;
};
const Root:React.FC=()=> <Composition id="CreativeDuel" component={Scene} fps={24} durationInFrames={360} width={1280} height={720}/>;
registerRoot(Root);
