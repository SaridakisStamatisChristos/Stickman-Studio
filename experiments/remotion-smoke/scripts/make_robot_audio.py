from pathlib import Path
import os, json
from kokoro_onnx import Kokoro
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly, butter, sosfilt
from math import gcd
R=48000; N=12*R;t=np.arange(N)/R; rng=np.random.default_rng(43); mix=np.zeros(N)
def put(a,start,gain=1):
 i=int(start*R); n=min(len(a),N-i)
 if n>0: mix[i:i+n]+=a[:n]*gain
def tone(freq,dur,decay=4):
 x=np.arange(int(dur*R))/R; return (np.sin(2*np.pi*freq*x)+.18*np.sin(2*np.pi*freq*2*x))*np.exp(-decay*x)*np.minimum(x/.012,1)
for i,f in enumerate([110,130.81,164.81,196,220]):
 mix+=.024*np.sin(2*np.pi*f*t+.35*np.sin(t*.5+i))*(.65+.35*np.sin(t*.7+i))*np.minimum(t/.8,1)*np.minimum((12-t)/1.2,1)
for i in range(16):
 st=i*.75; x=np.arange(int(.16*R))/R;put(np.sin(2*np.pi*(75*x-100*x*x))*np.exp(-25*x),st,.10)
for i in range(8):put(tone([440,523.25,659.25,783.99][i%4],.7,5),i*1.5+.2,.035)
for j in range(4):put(tone(500+j*105,.12,25),.5+j*.43,.05)
x=np.arange(int(1.8*R))/R; noise=sosfilt(butter(2,[450,4500],btype='bandpass',fs=R,output='sos'),rng.normal(size=len(x)));put(noise*(x/1.8)**2,3.35,.14)
x=np.arange(int(1.15*R))/R;put((np.sin(2*np.pi*(85*x-20*x*x))+.35*rng.normal(size=len(x)))*np.exp(-7*x),5.1,.22)
for i,f in enumerate([523.25,659.25,783.99,1046.5,1318.51,1567.98]):put(tone(f,1.35,3.5),5.2+i*.095,.09)
for i in range(14):put(tone(700+int(rng.integers(0,1100)),.25,13),5.45+i*.24,.024)
for i,f in enumerate([523.25,659.25,783.99]):put(tone(f,.9,4),9.2+i*.09,.065)
phrases=[(0.22,2.64,'A little robot found a chest.'),(2.7,5.30,'But inside, something shone.'),(5.42,8.90,'Two hundred fifty thousand stars.'),(8.98,11.80,'No AI video. Just code.')]
model_dir=Path(os.environ.get('KOKORO_MODEL_DIR',Path(__file__).resolve().parent.parent/'models'/'kokoro'))
voice=os.environ.get('KOKORO_VOICE','af_heart')
kokoro=Kokoro(str(model_dir/'kokoro-v1.0.int8.onnx'),str(model_dir/'voices-v1.0.bin'))
narration=np.zeros(N)
report={'backend':'kokoro-onnx','voice':voice,'sample_rate':R,'segments':[]}
for st,end,s in phrases:
 speed=1.0
 for attempt in range(5):
  v,sr=kokoro.create(s,voice=voice,speed=speed,lang='en-us')
  v=np.asarray(v,dtype=float).reshape(-1)
  assert len(v)>0 and np.isfinite(v).all()
  nz=np.flatnonzero(np.abs(v)>.002)
  assert len(nz)>0,'silent Kokoro output'
  v=v[max(0,nz[0]-int(.025*sr)):min(len(v),nz[-1]+int(.08*sr)+1)]
  if len(v)/sr<=end-st: break
  speed*=max(1.06,(len(v)/sr)/(end-st)*1.04)
 else: raise RuntimeError(f'Narration does not fit: {s}')
 g=gcd(sr,R);v=resample_poly(v,R//g,sr//g)
 v=sosfilt(butter(2,90,btype='highpass',fs=R,output='sos'),v)
 rms=float(np.sqrt(np.mean(v*v)))
 assert rms>.001
 v*=min(.17/rms,.66/(np.max(np.abs(v))+1e-8))
 ramp=min(int(.012*R),len(v)//2)
 if ramp:
  v[:ramp]*=np.linspace(0,1,ramp);v[-ramp:]*=np.linspace(1,0,ramp)
 i=int(st*R);j=i+len(v)
 assert j<=int(end*R)+1 and j<=N
 narration[i:j]+=v
 # Smooth music ducking around each utterance.
 left=max(0,i-int(.09*R));right=min(N,j+int(.18*R))
 mix[left:i]*=np.linspace(1,.46,i-left)
 mix[i:j]*=.46
 mix[j:right]*=np.linspace(.46,1,right-j)
 report['segments'].append({'text':s,'start':st,'end':j/R,'speed':speed,'rms':rms})
mix+=narration
out_dir=Path(__file__).resolve().parent.parent/'out';out_dir.mkdir(exist_ok=True)
wavfile.write(out_dir/'kokoro-narration.wav',R,np.int16(np.clip(narration,-1,1)*32767))
(out_dir/'voice-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
fade=np.minimum(t/.04,1)*np.minimum((12-t)/.22,1); mix=np.tanh(mix*1.15)*fade
out=Path(__file__).resolve().parent.parent/'public'/'soundtrack.wav'
out.parent.mkdir(exist_ok=True)
wavfile.write(out,R,np.int16(mix*32767))
