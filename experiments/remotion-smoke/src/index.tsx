import React from 'react';
import {AbsoluteFill, Composition, Easing, interpolate, registerRoot, staticFile, useCurrentFrame} from 'remotion';
import {Audio} from '@remotion/media';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const Robot: React.FC<{frame: number}> = ({frame}) => {
  const x = interpolate(frame, [0, 125, 160], [125, 585, 585], {...clamp, easing: Easing.out(Easing.cubic)});
  const moving = frame < 125 ? 1 : 0;
  const stride = Math.sin(frame * 0.6) * moving;
  const bob = Math.abs(Math.sin(frame * 0.6)) * moving * 4;
  const crouch = interpolate(frame, [148, 188], [0, 30], clamp);
  const tip = interpolate(frame, [150, 189], [0, 14], clamp);
  return <g transform={'translate(' + x + ',' + (515+bob+crouch) + ') rotate(' + tip + ')'}>
    <ellipse cx="0" cy="89" rx="54" ry="12" fill="#020810" opacity=".5" />
    <g stroke="#d9f4ff" strokeWidth="15" strokeLinecap="round" strokeLinejoin="round" fill="none">
      <path d={'M-18 18 L' +(-24+25*stride)+' 50 L'+(-34+36*stride)+' 86'} />
      <path d={'M18 18 L'+(24-25*stride)+' 50 L'+(34-36*stride)+' 86'}/>
      <path d={'M-28 -65 L'+(-48+13*stride)+' -25 L'+(-39+13*stride)+' 5'}/>
      <path d={'M28 -65 L'+(48-13*stride)+' -25 L'+(39-13*stride)+' 5'}/>
    </g>
    <rect x="-29" y="-82" width="58" height="105" rx="18" fill="#112a3b" stroke="#d9f4ff" strokeWidth="7"/>
    <rect x="-41" y="-153" width="82" height="66" rx="21" fill="#def6ff"/>
    <rect x="-28" y="-139" width="56" height="31" rx="11" fill="#082a3f"/>
    <circle cx="-14" cy="-124" r="5" fill="#67efff"/><circle cx="14" cy="-124" r="5" fill="#67efff"/>
    <rect x="-12" y="-35" width="24" height="11" rx="5" fill="#6dfaff"/>
    <path d="M-22 -150 L-22 -166 M22 -150 L22 -166" stroke="#b9e7ff" strokeWidth="5"/>
  </g>;
};

const Scene: React.FC = () => {
  const frame = useCurrentFrame();
  const light = interpolate(frame, [87, 135], [0, 1], clamp);
  const pulse = (0.8 + Math.sin(frame * .12) * .2) * light;
  const camera = interpolate(frame, [0, 180, 239], [0, -70, -145], clamp);
  const header = interpolate(frame, [8, 29], [0, 1], clamp) * interpolate(frame, [55, 75], [1, 0], clamp);
  const caption = interpolate(frame, [177, 205], [0, 1], clamp);
  const ending = interpolate(frame, [224, 239], [1, 0], clamp);
  return <AbsoluteFill style={{background:'#050b19', overflow:'hidden', color:'#edf7ff', fontFamily:'Arial,sans-serif'}}>
    <Audio src={staticFile('soundtrack.wav')} />
    <svg width="1280" height="720" viewBox="0 0 1280 720" style={{position:'absolute'}}>
      <defs>
        <linearGradient id="sky" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#040715"/><stop offset="1" stopColor="#18374b"/></linearGradient>
        <linearGradient id="road" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#1a2e3c"/><stop offset="1" stopColor="#030614"/></linearGradient>
        <radialGradient id="glow"><stop offset="0" stopColor="#f0ffff"/><stop offset=".16" stopColor="#6ffaff" stopOpacity=".9"/><stop offset=".52" stopColor="#49beff" stopOpacity=".3"/><stop offset="1" stopColor="#49cfff" stopOpacity="0"/></radialGradient>
      </defs>
      <rect width="1280" height="720" fill="url(#sky)"/>
      {Array.from({length:35},(_,i)=><circle key={i} cx={(i*179+53)%1280} cy={(i*79+29)%360} r={i%4===0?2:1} fill="#b7eaff" opacity=".45"/>)}
      <g transform={'translate('+(camera*.35)+',0)'}>
        {Array.from({length:14},(_,i)=>{const h=170+((i*83)%230);const x=i*111-90;return <g key={i}>
          <rect x={x} y={535-h} width="100" height={h+90} fill={i%3===0?'#0b1826':'#102536'}/>
          {Array.from({length:9},(_,j)=><rect key={j} x={x+13+(j%3)*27} y={549-h+Math.floor(j/3)*34} width="10" height="15" fill="#aae8ff" opacity={(i+j)%5===0?.45:.06}/>)}
        </g>})}
      </g>
      <g transform={'translate('+(camera*.6)+',0)'}>
        {Array.from({length:8},(_,i)=>{const h=95+((i*67)%170);return <rect key={i} x={i*205-110} y={560-h} width="180" height={h+35} fill="#142a39"/>})}
      </g>
      <rect x="0" y="565" width="1280" height="155" fill="url(#road)"/>
      <path d="M0 565 H1280" stroke="#3c586b" strokeWidth="4"/>
      <g transform={'translate('+camera+',0)'}>
        <path d="M0 655 H1280" stroke="#406173" strokeWidth="3" strokeDasharray="100 58" opacity=".5"/>
        <path d="M680 566 L720 582 L780 599" stroke="#263f4e" strokeWidth="5" fill="none"/>
        <circle cx="735" cy="578" r="180" fill="url(#glow)" opacity={pulse}/>
        <circle cx="735" cy="578" r="65" fill="url(#glow)" opacity={pulse}/>
        <circle cx="735" cy="578" r={4+3*pulse} fill="#ecffff" opacity={light}/>
        <Robot frame={frame}/>
      </g>
    </svg>
    <div style={{position:'absolute',top:97,left:100,fontWeight:800,fontSize:54,letterSpacing:7,opacity:header*ending,textShadow:'0 0 25px #26c3ff'}}>THE LAST SIGNAL</div>
    <div style={{position:'absolute',bottom:95,left:100,fontWeight:700,fontSize:35,letterSpacing:2,opacity:caption*ending,textShadow:'0 0 18px #3af6ff'}}>Something was still alive.</div>
  </AbsoluteFill>;
};

const Root: React.FC = () => <Composition id="StickmanSmoke" component={Scene} fps={24} durationInFrames={240} width={1280} height={720}/>;
registerRoot(Root);
